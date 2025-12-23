#!/usr/bin/env python3
"""
Test microphone input
"""
import pyaudio
import wave
import sys

print("🎤 Microphone Test")
print("=" * 50)

try:
    p = pyaudio.PyAudio()
    
    # List audio devices
    print("\nAvailable audio devices:")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            print(f"  [{i}] {info['name']} (Input channels: {info['maxInputChannels']})")
    
    # Test recording
    print("\n🎙️  Recording 3 seconds of audio...")
    print("Speak now!")
    
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=1024
    )
    
    frames = []
    for _ in range(0, int(16000 / 1024 * 3)):
        data = stream.read(1024)
        frames.append(data)
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Save to file
    output_file = "/tmp/arc_mic_test.wav"
    wf = wave.open(output_file, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(16000)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    print(f"✅ Recording saved to: {output_file}")
    print("Playing back...")
    
    import subprocess
    subprocess.run(["afplay", output_file])
    
    print("✅ Microphone test complete!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
