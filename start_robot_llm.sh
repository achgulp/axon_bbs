#!/bin/bash
# Start LLM server for AiRobotWars

LLAMA_DIR="$HOME/llama.cpp"
# Using Llama-3.2-1B - compact and good instruction following
MODEL="$LLAMA_DIR/models/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
PORT=8081

# Check if model exists
if [ ! -f "$MODEL" ]; then
    echo "❌ Model not found: $MODEL"
    echo "Available models:"
    ls -lh "$LLAMA_DIR/models/"*.gguf 2>/dev/null || echo "No .gguf files found"
    exit 1
fi

# Check if server binary exists
SERVER="$LLAMA_DIR/build/bin/llama-server"
if [ ! -x "$SERVER" ]; then
    echo "❌ llama-server not found at: $SERVER"
    echo "Build it with: cd $LLAMA_DIR && cmake -B build && cmake --build build -t llama-server"
    exit 1
fi

echo "🤖 Starting Robot Wars AI Server"
echo "   Model: Qwen2.5-1.5B-Instruct-Q6_K"
echo "   Port: $PORT"
echo "   Context: 1024 tokens"
echo ""

cd "$LLAMA_DIR"
export LD_LIBRARY_PATH="$LLAMA_DIR/build/bin:$LD_LIBRARY_PATH"
exec "$SERVER" -m "$MODEL" --port $PORT -c 1024 --threads 4
