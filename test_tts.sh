#!/bin/bash
# Simple TTS Test using Piper CLI

echo "Testing Piper TTS..."
echo "Hello, I am ARC, your autonomous reasoning companion." | piper \
  --model models/piper/en_US-lessac-medium.onnx \
  --output_file /tmp/arc_test.wav

echo "Playing audio..."
afplay /tmp/arc_test.wav

echo "✅ TTS test complete!"
