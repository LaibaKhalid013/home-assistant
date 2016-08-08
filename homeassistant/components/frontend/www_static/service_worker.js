"use strict";function setOfCachedUrls(e){return e.keys().then(function(e){return e.map(function(e){return e.url})}).then(function(e){return new Set(e)})}var precacheConfig=[["/","172d13ac3f54c378c68b2acacea3081b"],["/frontend/panels/dev-event-3cc881ae8026c0fba5aa67d334a3ab2b.html","e22ed0d2d10777c87eb9620d81f525b4"],["/frontend/panels/dev-info-34e2df1af32e60fffcafe7e008a92169.html","7e939dc762dc0c0ec769db4ea76a4b09"],["/frontend/panels/dev-service-bb5c587ada694e0fd42ceaaedd6fe6aa.html","782c4860c5e8ab274231ba9dfd528f29"],["/frontend/panels/dev-state-4608326978256644c42b13940c028e0a.html","26758b741ac1b7c8e9cfcb24762d8774"],["/frontend/panels/dev-template-0a099d4589636ed3038a3e9f020468a7.html","99114026cf9193263c74cc25f9f6a469"],["/frontend/panels/map-39d4793bb67cedbbdbd1d79bdadc9c3f.html","67fde0ba390387969c2a603e52007aea"],["/static/core-a2abcabdb2e5f1fa0dd4d03c77b99642.js","6bde61226104b1fcdea3c55bf8fe2f9b"],["/static/frontend-ac2faa47ed93a8611cd255b0610d3e24.html","fd737eb9de46d1151e6414504f72ea24"],["/static/mdi-f6c6cc64c2ec38a80e91f801b41119b3.html","e010f32322ed6f66916c7c09dbba4acd"],["static/fonts/roboto/Roboto-Bold.ttf","d329cc8b34667f114a95422aaad1b063"],["static/fonts/roboto/Roboto-Light.ttf","7b5fb88f12bec8143f00e21bc3222124"],["static/fonts/roboto/Roboto-Medium.ttf","fe13e4170719c2fc586501e777bde143"],["static/fonts/roboto/Roboto-Regular.ttf","ac3f799d5bbaf5196fab15ab8de8431c"],["static/icons/favicon-192x192.png","419903b8422586a7e28021bbe9011175"],["static/icons/favicon.ico","04235bda7843ec2fceb1cbe2bc696cf4"],["static/images/card_media_player_bg.png","a34281d1c1835d338a642e90930e61aa"],["static/webcomponents-lite.min.js","b0f32ad3c7749c40d486603f31c9d8b1"]],cacheName="sw-precache-v2--"+(self.registration?self.registration.scope:""),ignoreUrlParametersMatching=[/^utm_/],addDirectoryIndex=function(e,t){var a=new URL(e);return"/"===a.pathname.slice(-1)&&(a.pathname+=t),a.toString()},createCacheKey=function(e,t,a,n){var c=new URL(e);return n&&c.toString().match(n)||(c.search+=(c.search?"&":"")+encodeURIComponent(t)+"="+encodeURIComponent(a)),c.toString()},isPathWhitelisted=function(e,t){if(0===e.length)return!0;var a=new URL(t).pathname;return e.some(function(e){return a.match(e)})},stripIgnoredUrlParameters=function(e,t){var a=new URL(e);return a.search=a.search.slice(1).split("&").map(function(e){return e.split("=")}).filter(function(e){return t.every(function(t){return!t.test(e[0])})}).map(function(e){return e.join("=")}).join("&"),a.toString()},hashParamName="_sw-precache",urlsToCacheKeys=new Map(precacheConfig.map(function(e){var t=e[0],a=e[1],n=new URL(t,self.location),c=createCacheKey(n,hashParamName,a,!1);return[n.toString(),c]}));self.addEventListener("install",function(e){e.waitUntil(caches.open(cacheName).then(function(e){return setOfCachedUrls(e).then(function(t){return Promise.all(Array.from(urlsToCacheKeys.values()).map(function(a){if(!t.has(a))return e.add(new Request(a,{credentials:"same-origin"}))}))})}).then(function(){return self.skipWaiting()}))}),self.addEventListener("activate",function(e){var t=new Set(urlsToCacheKeys.values());e.waitUntil(caches.open(cacheName).then(function(e){return e.keys().then(function(a){return Promise.all(a.map(function(a){if(!t.has(a.url))return e.delete(a)}))})}).then(function(){return self.clients.claim()}))}),self.addEventListener("fetch",function(e){if("GET"===e.request.method){var t,a=stripIgnoredUrlParameters(e.request.url,ignoreUrlParametersMatching);t=urlsToCacheKeys.has(a);var n="index.html";!t&&n&&(a=addDirectoryIndex(a,n),t=urlsToCacheKeys.has(a));var c="/";!t&&c&&"navigate"===e.request.mode&&isPathWhitelisted(["^((?!(static|api|local|service_worker.js)).)*$"],e.request.url)&&(a=new URL(c,self.location).toString(),t=urlsToCacheKeys.has(a)),t&&e.respondWith(caches.open(cacheName).then(function(e){return e.match(urlsToCacheKeys.get(a))}).catch(function(t){return console.warn('Couldn\'t serve response for "%s" from cache: %O',e.request.url,t),fetch(e.request)}))}});