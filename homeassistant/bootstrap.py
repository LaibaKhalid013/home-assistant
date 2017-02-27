"""Provides methods to bootstrap a home assistant instance."""
import asyncio
import logging
import logging.handlers
import os
import sys
from collections import OrderedDict

from types import ModuleType
from typing import Any, Optional, Dict

import voluptuous as vol

import homeassistant.components as core_components
from homeassistant.components import persistent_notification
import homeassistant.config as conf_util
import homeassistant.core as core
from homeassistant.const import EVENT_HOMEASSISTANT_CLOSE
import homeassistant.loader as loader
import homeassistant.util.package as pkg_util
from homeassistant.util.async import (
    run_coroutine_threadsafe, run_callback_threadsafe)
from homeassistant.util.logging import AsyncHandler
from homeassistant.util.yaml import clear_secret_cache
from homeassistant.const import EVENT_COMPONENT_LOADED, PLATFORM_FORMAT
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    event_decorators, service, config_per_platform, extract_domain_configs)
from homeassistant.helpers.signal import async_register_signal_handling

_LOGGER = logging.getLogger(__name__)

ATTR_COMPONENT = 'component'

DATA_PERSISTENT_ERRORS = 'bootstrap_persistent_errors'
DATA_SETUP = 'setup_tasks'
DATA_PLATFORM = 'platform_events'
DATA_PIP_LOCK = 'pip_lock'

ERROR_LOG_FILENAME = 'home-assistant.log'
HA_COMPONENT_URL = '[{}](https://home-assistant.io/components/{}/)'


def setup_component(hass: core.HomeAssistant, domain: str,
                    config: Optional[Dict]=None) -> bool:
    """Setup a component and all its dependencies."""
    return run_coroutine_threadsafe(
        async_setup_component(hass, domain, config), loop=hass.loop).result()


@asyncio.coroutine
def async_setup_component(hass: core.HomeAssistant, domain: str,
                          config: Optional[Dict]=None) -> bool:
    """Setup a component and all its dependencies.

    This method is a coroutine.
    """
    if domain in hass.config.components:
        _LOGGER.debug('Component %s already set up.', domain)
        return True

    if not loader.PREPARED:
        yield from hass.loop.run_in_executor(None, loader.prepare, hass)

    if config is None:
        config = {}

    components = loader.load_order_component(domain)

    # OrderedSet is empty if component or dependencies could not be resolved
    if not components:
        _async_persistent_notification(hass, domain, True)
        return False

    setup_events = hass.data.get(DATA_SETUP)
    if setup_events is None:
        hass.data[DATA_PLATFORM] = {}
        setup_events = hass.data[DATA_SETUP] = {}

    tasks = []
    for component in components:
        if component not in setup_events:
            setup_events[component] = hass.async_add_job(
                _async_setup_component(hass, component, config))
        tasks.append(setup_events[component])

    if tasks:
        results = yield from asyncio.gather(*tasks, loop=hass.loop)
        for idx, res in enumerate(results):
            if not res:
                _LOGGER.error('Component %s failed to setup', components[idx])
                _async_persistent_notification(hass, components[idx], True)
                return False

    return True


@asyncio.coroutine
def _async_handle_requirements(hass: core.HomeAssistant, component,
                               name: str) -> bool:
    """Install the requirements for a component.

    This method is a coroutine.
    """
    if hass.config.skip_pip or not hasattr(component, 'REQUIREMENTS'):
        return True

    pip_lock = hass.data.get(DATA_PIP_LOCK)
    if pip_lock is None:
        pip_lock = hass.data[DATA_PIP_LOCK] = asyncio.Lock(loop=hass.loop)

    def pip_install(mod):
        """Install packages."""
        return pkg_util.install_package(mod, target=hass.config.path('deps'))

    with (yield from pip_lock):
        for req in component.REQUIREMENTS:
            ret = yield from hass.loop.run_in_executor(None, pip_install, req)
            if not ret:
                _LOGGER.error('Not initializing %s because could not install '
                              'dependency %s', name, req)
                _async_persistent_notification(hass, name)
                return False

    return True


@asyncio.coroutine
def _async_setup_component(hass: core.HomeAssistant,
                           domain: str, config) -> bool:
    """Setup a component for Home Assistant.

    This method is a coroutine.
    """
    # pylint: disable=too-many-return-statements
    if domain in hass.config.components:
        return True

    setup_events = hass.data[DATA_SETUP]

    # is setup or in progress
    if setup_events[domain].done():
        return setup_events[domain].result()

    component = loader.get_component(domain)
    if component is None:
        return False

    config = conf_util.async_extract_component_config(hass, config, domain)

    if config is None:
        return False

    # wait until all dependencies are setup
    if hasattr(component, 'DEPENDENCIES'):
        tasks = []
        for dep in component.DEPENDENCIES:
            if dep in setup_events:
                tasks.append(setup_events[dep])
        if tasks:
            results = yield from asyncio.gather(*tasks, loop=hass.loop)
            if any(res is not True for res in results):
                return False

    async_comp = hasattr(component, 'async_setup')

    try:
        _LOGGER.info("Setting up %s", domain)
        if async_comp:
            result = yield from component.async_setup(hass, config)
        else:
            result = yield from hass.loop.run_in_executor(
                None, component.setup, hass, config)
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception('Error during setup of component %s', domain)
        _async_persistent_notification(hass, domain, True)
        return False

    if result is False:
        _LOGGER.error('component %s failed to initialize', domain)
        _async_persistent_notification(hass, domain, True)
        return False
    elif result is not True:
        _LOGGER.error('component %s did not return boolean if setup '
                      'was successful. Disabling component.', domain)
        loader.set_component(domain, None)
        _async_persistent_notification(hass, domain, True)
        return False

    hass.config.components.add(component.DOMAIN)

    hass.bus.async_fire(
        EVENT_COMPONENT_LOADED, {ATTR_COMPONENT: component.DOMAIN}
    )

    # wait until entities are setup
    if domain in hass.data[DATA_PLATFORM]:
        yield from hass.data[DATA_PLATFORM][domain].wait()

    return True


def prepare_setup_component(hass: core.HomeAssistant, config: dict,
                            domain: str):
    """Prepare setup of a component and return processed config."""
    return run_coroutine_threadsafe(
        async_prepare_setup_component(hass, config, domain), loop=hass.loop
    ).result()


def prepare_setup_platform(hass: core.HomeAssistant, config, domain: str,
                           platform_name: str) -> Optional[ModuleType]:
    """Load a platform and makes sure dependencies are setup."""
    return run_coroutine_threadsafe(
        async_prepare_setup_platform(hass, config, domain, platform_name),
        loop=hass.loop
    ).result()


@asyncio.coroutine
def async_prepare_setup_platform(hass: core.HomeAssistant, config, domain: str,
                                 platform_name: str) \
                                 -> Optional[ModuleType]:
    """Load a platform and makes sure dependencies are setup.

    This method is a coroutine.
    """
    if not loader.PREPARED:
        yield from hass.loop.run_in_executor(None, loader.prepare, hass)

    platform_path = PLATFORM_FORMAT.format(domain, platform_name)

    platform = loader.get_platform(domain, platform_name)

    # Not found
    if platform is None:
        _LOGGER.error('Unable to find platform %s', platform_path)
        _async_persistent_notification(hass, platform_path)
        return None

    # Already loaded
    elif platform_path in hass.config.components:
        return platform

    # Load dependencies
    for component in getattr(platform, 'DEPENDENCIES', []):
        if component in loader.DEPENDENCY_BLACKLIST:
            raise HomeAssistantError(
                '{} is not allowed to be a dependency.'.format(component))

        res = yield from async_setup_component(hass, component, config)
        if not res:
            _LOGGER.error(
                'Unable to prepare setup for platform %s because '
                'dependency %s could not be initialized', platform_path,
                component)
            _async_persistent_notification(hass, platform_path, True)
            return None

    res = yield from _async_handle_requirements(hass, platform, platform_path)
    if not res:
        return None

    return platform


def from_config_dict(config: Dict[str, Any],
                     hass: Optional[core.HomeAssistant]=None,
                     config_dir: Optional[str]=None,
                     enable_log: bool=True,
                     verbose: bool=False,
                     skip_pip: bool=False,
                     log_rotate_days: Any=None) \
                     -> Optional[core.HomeAssistant]:
    """Try to configure Home Assistant from a config dict.

    Dynamically loads required components and its dependencies.
    """
    if hass is None:
        hass = core.HomeAssistant()
        if config_dir is not None:
            config_dir = os.path.abspath(config_dir)
            hass.config.config_dir = config_dir
            mount_local_lib_path(config_dir)

    # run task
    hass = hass.loop.run_until_complete(
        async_from_config_dict(
            config, hass, config_dir, enable_log, verbose, skip_pip,
            log_rotate_days)
    )

    return hass


@asyncio.coroutine
def async_from_config_dict(config: Dict[str, Any],
                           hass: core.HomeAssistant,
                           config_dir: Optional[str]=None,
                           enable_log: bool=True,
                           verbose: bool=False,
                           skip_pip: bool=False,
                           log_rotate_days: Any=None) \
                           -> Optional[core.HomeAssistant]:
    """Try to configure Home Assistant from a config dict.

    Dynamically loads required components and its dependencies.
    This method is a coroutine.
    """
    hass.async_track_tasks()

    core_config = config.get(core.DOMAIN, {})

    try:
        yield from conf_util.async_process_ha_core_config(hass, core_config)
    except vol.Invalid as ex:
        conf_util.async_log_exception(ex, 'homeassistant', core_config, hass)
        return None

    yield from hass.loop.run_in_executor(
        None, conf_util.process_ha_config_upgrade, hass)

    if enable_log:
        async_enable_logging(hass, verbose, log_rotate_days)

    hass.config.skip_pip = skip_pip
    if skip_pip:
        _LOGGER.warning('Skipping pip installation of required modules. '
                        'This may cause issues.')

    if not loader.PREPARED:
        yield from hass.loop.run_in_executor(None, loader.prepare, hass)

    # Merge packages
    conf_util.merge_packages_config(
        config, core_config.get(conf_util.CONF_PACKAGES, {}))

    # Make a copy because we are mutating it.
    # Use OrderedDict in case original one was one.
    # Convert values to dictionaries if they are None
    new_config = OrderedDict()
    for key, value in config.items():
        new_config[key] = value or {}
    config = new_config

    # Filter out the repeating and common config section [homeassistant]
    components = set(key.split(' ')[0] for key in config.keys()
                     if key != core.DOMAIN)

    # setup components
    # pylint: disable=not-an-iterable
    res = yield from core_components.async_setup(hass, config)
    if not res:
        _LOGGER.error('Home Assistant core failed to initialize. '
                      'Further initialization aborted.')
        return hass

    yield from persistent_notification.async_setup(hass, config)

    _LOGGER.info('Home Assistant core initialized')

    # Give event decorators access to HASS
    event_decorators.HASS = hass
    service.HASS = hass

    # Setup the components
    dependency_blacklist = loader.DEPENDENCY_BLACKLIST - set(components)

    setup_events = hass.data.get(DATA_SETUP)
    if setup_events is None:
        hass.data[DATA_PLATFORM] = {}
        setup_events = hass.data[DATA_SETUP] = {}

    tasks = []
    for domain in loader.load_order_components(components):
        if domain in dependency_blacklist:
            raise HomeAssistantError(
                '{} is not allowed to be a dependency'.format(domain))

        # setup task
        if domain not in hass.data[DATA_SETUP]:
            setup_events[domain] = hass.async_add_job(
                _async_setup_component(hass, domain, config)
            )
        tasks.append(setup_events[domain])

    if tasks:
        yield from asyncio.wait(tasks, loop=hass.loop)

    yield from hass.async_stop_track_tasks()

    async_register_signal_handling(hass)
    return hass


def from_config_file(config_path: str,
                     hass: Optional[core.HomeAssistant]=None,
                     verbose: bool=False,
                     skip_pip: bool=True,
                     log_rotate_days: Any=None):
    """Read the configuration file and try to start all the functionality.

    Will add functionality to 'hass' parameter if given,
    instantiates a new Home Assistant object if 'hass' is not given.
    """
    if hass is None:
        hass = core.HomeAssistant()

    # run task
    hass = hass.loop.run_until_complete(
        async_from_config_file(
            config_path, hass, verbose, skip_pip, log_rotate_days)
    )

    return hass


@asyncio.coroutine
def async_from_config_file(config_path: str,
                           hass: core.HomeAssistant,
                           verbose: bool=False,
                           skip_pip: bool=True,
                           log_rotate_days: Any=None):
    """Read the configuration file and try to start all the functionality.

    Will add functionality to 'hass' parameter.
    This method is a coroutine.
    """
    # Set config dir to directory holding config file
    config_dir = os.path.abspath(os.path.dirname(config_path))
    hass.config.config_dir = config_dir
    yield from hass.loop.run_in_executor(
        None, mount_local_lib_path, config_dir)

    async_enable_logging(hass, verbose, log_rotate_days)

    try:
        config_dict = yield from hass.loop.run_in_executor(
            None, conf_util.load_yaml_config_file, config_path)
    except HomeAssistantError:
        return None
    finally:
        clear_secret_cache()

    hass = yield from async_from_config_dict(
        config_dict, hass, enable_log=False, skip_pip=skip_pip)
    return hass


@core.callback
def async_enable_logging(hass: core.HomeAssistant, verbose: bool=False,
                         log_rotate_days=None) -> None:
    """Setup the logging.

    This method must be run in the event loop.
    """
    logging.basicConfig(level=logging.INFO)
    fmt = ("%(asctime)s %(levelname)s (%(threadName)s) "
           "[%(name)s] %(message)s")
    colorfmt = "%(log_color)s{}%(reset)s".format(fmt)
    datefmt = '%y-%m-%d %H:%M:%S'

    # suppress overly verbose logs from libraries that aren't helpful
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)

    try:
        from colorlog import ColoredFormatter
        logging.getLogger().handlers[0].setFormatter(ColoredFormatter(
            colorfmt,
            datefmt=datefmt,
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red',
            }
        ))
    except ImportError:
        pass

    # Log errors to a file if we have write access to file or config dir
    err_log_path = hass.config.path(ERROR_LOG_FILENAME)
    err_path_exists = os.path.isfile(err_log_path)

    # Check if we can write to the error log if it exists or that
    # we can create files in the containing directory if not.
    if (err_path_exists and os.access(err_log_path, os.W_OK)) or \
       (not err_path_exists and os.access(hass.config.config_dir, os.W_OK)):

        if log_rotate_days:
            err_handler = logging.handlers.TimedRotatingFileHandler(
                err_log_path, when='midnight', backupCount=log_rotate_days)
        else:
            err_handler = logging.FileHandler(
                err_log_path, mode='w', delay=True)

        err_handler.setLevel(logging.INFO if verbose else logging.WARNING)
        err_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

        async_handler = AsyncHandler(hass.loop, err_handler)

        @asyncio.coroutine
        def async_stop_async_handler(event):
            """Cleanup async handler."""
            logging.getLogger('').removeHandler(async_handler)
            yield from async_handler.async_close(blocking=True)

        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_CLOSE, async_stop_async_handler)

        logger = logging.getLogger('')
        logger.addHandler(async_handler)
        logger.setLevel(logging.INFO)

    else:
        _LOGGER.error(
            'Unable to setup error log %s (access denied)', err_log_path)


@core.callback
def _async_persistent_notification(hass: core.HomeAssistant, component: str,
                                   link: Optional[bool]=False):
    """Print a persistent notification.

    This method must be run in the event loop.
    """
    errors = hass.data.get(DATA_PERSISTENT_ERRORS)

    if errors is None:
        errors = hass.data[DATA_PERSISTENT_ERRORS] = {}

    errors[component] = errors.get(component) or link
    _lst = [HA_COMPONENT_URL.format(name.replace('_', '-'), name)
            if link else name for name, link in errors.items()]
    message = ('The following components and platforms could not be set up:\n'
               '* ' + '\n* '.join(list(_lst)) + '\nPlease check your config')
    persistent_notification.async_create(
        hass, message, 'Invalid config', 'invalid_config')


def mount_local_lib_path(config_dir: str) -> str:
    """Add local library to Python Path.

    Async friendly.
    """
    deps_dir = os.path.join(config_dir, 'deps')
    if deps_dir not in sys.path:
        sys.path.insert(0, os.path.join(config_dir, 'deps'))
    return deps_dir
