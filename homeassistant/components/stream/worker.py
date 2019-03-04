"""Proides the worker thread needed for processing streams."""
import asyncio
from fractions import Fraction
import io

from .const import AUDIO_SAMPLE_RATE
from .core import Segment, StreamBuffer


def generate_audio_frame():
    """Generate a blank audio frame."""
    from av import AudioFrame
    audio_frame = AudioFrame(format='dbl', layout='mono', samples=1024)
    audio_bytes = b''.join(b'\x00\x00\x00\x00\x00\x00\x00\x00'
                           for i in range(0, 1024))
    audio_frame.planes[0].update(audio_bytes)
    audio_frame.sample_rate = AUDIO_SAMPLE_RATE
    audio_frame.time_base = Fraction(1, AUDIO_SAMPLE_RATE)
    return audio_frame


def create_stream_buffer(stream_output, video_stream, audio_frame):
    """Create a new StreamBuffer."""
    import av
    a_packet = None
    segment = io.BytesIO()
    output = av.open(
        segment, mode='w', format=stream_output.format)
    vstream = output.add_stream(
        stream_output.video_codec, video_stream.rate)
    # Fix format
    vstream.codec_context.format = \
        video_stream.codec_context.format
    # Check if audio is requested
    astream = None
    if stream_output.audio_codec:
        astream = output.add_stream(
            stream_output.audio_codec, AUDIO_SAMPLE_RATE)
        # Need to do it multiple times for some reason
        while not a_packet:
            a_packets = astream.encode(audio_frame)
            if a_packets:
                a_packet = a_packets[0]
    return (a_packet, StreamBuffer(segment, output, vstream, astream))


def stream_worker(hass, stream, quit_event):
    """Handle consuming streams."""
    import av
    try:
        video_stream = stream.container.streams.video[0]
    except (KeyError, IndexError):
        hass.getLogger().error("Stream has no video")
        return

    audio_frame = generate_audio_frame()

    outputs = {}
    first_packet = True
    sequence = 1
    audio_packets = {}

    while not quit_event.is_set():
        try:
            packet = next(stream.container.demux(video_stream))
            if packet.dts is None:
                # If we get a "flushing" packet, the stream is done
                raise StopIteration
        except (av.AVError, StopIteration):
            # End of stream, clear listeners and stop thread
            for fmt, _ in outputs.items():
                asyncio.run_coroutine_threadsafe(
                    stream.outputs[fmt].put(None), hass.loop)
            break

        # Reset segment on every keyframe
        if packet.is_keyframe:
            # Save segment to outputs
            segment_duration = (packet.pts * packet.time_base) / sequence
            for fmt, buffer in outputs.items():
                # Flush streams
                for packet in buffer.vstream.encode():
                    buffer.output.mux(packet)
                if buffer.astream:
                    for packet in buffer.astream.encode():
                        buffer.output.mux(packet)
                buffer.output.close()
                del audio_packets[buffer.astream]
                if stream.outputs.get(fmt):
                    asyncio.run_coroutine_threadsafe(
                        stream.outputs[fmt].put(Segment(
                            sequence, buffer.segment, segment_duration
                        )), hass.loop)

            # Clear outputs and increment sequence
            outputs = {}
            if not first_packet:
                sequence += 1

            # Initialize outputs
            for stream_output in stream.outputs.values():
                if video_stream.name != stream_output.video_codec:
                    continue

                a_packet, buffer = create_stream_buffer(
                    stream_output, video_stream, audio_frame)
                audio_packets[buffer.astream] = a_packet
                outputs[stream_output.format] = buffer

        # First video packet tends to have a weird dts/pts
        if first_packet:
            packet.dts = 0
            packet.pts = 0
            first_packet = False

        # Store packets on each output
        for buffer in outputs.values():
            # Check if the format requires audio
            if audio_packets.get(buffer.astream):
                a_packet = audio_packets[buffer.astream]
                a_time_base = a_packet.time_base

                # Determine video start timestamp and duration
                video_start = packet.pts * packet.time_base
                video_duration = packet.duration * packet.time_base

                if packet.is_keyframe:
                    # Set first audio packet in sequence to equal video pts
                    a_packet.pts = int(video_start / a_time_base)
                    a_packet.dts = int(video_start / a_time_base)

                # Determine target end timestamp for audio
                target_pts = int((video_start + video_duration) / a_time_base)
                while a_packet.pts < target_pts:
                    # Mux audio packet and adjust points until target hit
                    buffer.output.mux(a_packet)
                    a_packet.pts += a_packet.duration
                    a_packet.dts += a_packet.duration
                    audio_packets[buffer.astream] = a_packet

            # Assign the video packet to the new stream & mux
            packet.stream = buffer.vstream
            buffer.output.mux(packet)
