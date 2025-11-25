# Quick Start Guide - SmartGlass AI Agent

## 🚀 Getting Started in 5 Minutes

### Step 1: Installation

```bash
# Clone the repository
git clone https://github.com/farmountain/SmartGlass-AI-Agent.git
cd SmartGlass-AI-Agent

# Install dependencies
pip install -r requirements.txt
```

**Note**: First installation may take 5-10 minutes as it downloads the models.

### Step 2: Test Basic Functionality

```python
from src.smartglass_agent import SmartGlassAgent

# Initialize agent (models will be downloaded automatically)
agent = SmartGlassAgent()

# Generate a simple response
response = agent.generate_response("Hello, what can you do?")
print(response)
```

### Step 3: Try Vision Understanding

```python
from PIL import Image

# Load an image (or use your Meta Ray-Ban photo)
image = Image.open("your_photo.jpg")

# Analyze the scene
scene = agent.analyze_scene(image)
print(scene['description'])

# Identify objects
objects = ['car', 'person', 'building', 'tree', 'sky']
identified = agent.identify_object(image, objects)
print(f"I see: {identified}")
```

### Step 4: Test Audio Processing

```python
# Transcribe audio (from Meta Ray-Ban recording)
text = agent.process_audio_command("audio_recording.wav")
print(f"You said: {text}")
```

### Step 5: Full Multimodal Experience

```python
# Combine audio, vision, and language
result = agent.process_multimodal_query(
    audio_input="command.wav",  # Your voice command
    image_input="scene.jpg"      # What you're looking at
)

query = result.get("query", "<unknown query>") if isinstance(result, dict) else "<unknown query>"
context = result.get("visual_context", "<no context>") if isinstance(result, dict) else "<no context>"
response_text = result.get("response", result) if isinstance(result, dict) else result

print(f"Query: {query}")
print(f"Context: {context}")
print(f"Response: {response_text}")

# Optional structured outputs
if isinstance(result, dict):
    print(f"Actions: {result.get('actions', [])}")
    print(f"Raw payload: {result.get('raw', {})}")
```

## 📓 Google Colab (No Installation Required!)

The easiest way to get started is using Google Colab:

1. Open the notebook: [SmartGlass_AI_Agent_Meta_RayBan.ipynb](SmartGlass_AI_Agent_Meta_RayBan.ipynb)
2. Click "Open in Colab" badge
3. Run all cells
4. Upload your Meta Ray-Ban photos/audio for testing

## 🎯 Common Use Cases

### Use Case 1: "What am I looking at?"

```python
response = agent.help_identify(
    image="photo.jpg",
    text_query="What do you see?"
)
print(response)
```

### Use Case 2: Find Your Lost Items

```python
items = ['keys', 'phone', 'wallet', 'glasses']
found = agent.identify_object(room_photo, items)
print(f"I found your {found}")
```

### Use Case 3: Navigation Help

```python
locations = ['indoor hallway', 'outdoor street', 'staircase', 'elevator']
location = agent.identify_object(view_photo, locations)
print(f"You are at: {location}")
```

### Use Case 4: Voice-Controlled Assistant

```python
# Record voice command on Meta Ray-Ban
# Transfer audio file
# Process with agent

command = agent.process_audio_command("voice_cmd.wav")
response = agent.generate_response(command)
print(response)
```

## ⚙️ Configuration

### For Faster Performance (Lower Accuracy)

```python
agent = SmartGlassAgent(
    whisper_model="tiny",  # Fastest
    gpt2_model="gpt2"      # Smallest
)
```

### For Better Accuracy (Slower)

```python
agent = SmartGlassAgent(
    whisper_model="small",    # More accurate
    gpt2_model="gpt2-medium"  # Better generation
)
```

### Recommended for Meta Ray-Ban (Balance)

```python
agent = SmartGlassAgent(
    whisper_model="base",  # Good balance
    gpt2_model="gpt2"      # Fast and efficient
)
```

## 💡 Tips

1. **First Run**: Models will be downloaded automatically (500MB-2GB)
2. **GPU**: If available, the agent will automatically use GPU for faster processing
3. **Images**: Works with JPG, PNG, and most image formats
4. **Audio**: Supports WAV, MP3, and most audio formats
5. **Languages**: Whisper supports 90+ languages for transcription

## 🐛 Troubleshooting

### Issue: "Out of Memory"
**Solution**: Use smaller models:
```python
agent = SmartGlassAgent(whisper_model="tiny", gpt2_model="gpt2")
```

### Issue: "Model download failed"
**Solution**: Check internet connection and try again. Models are cached after first download.

### Issue: "Slow processing"
**Solution**: 
- Use GPU if available
- Use smaller models
- Process lower resolution images

### Issue: "Import errors"
**Solution**: 
```bash
pip install --upgrade -r requirements.txt
```

## 📚 Next Steps

1. Check `examples/` directory for more examples
2. Read the full documentation in `README.md`
3. Try the Colab notebook for interactive testing
4. Customize the agent for your specific use case

## 🤝 Need Help?

- Open an issue on GitHub
- Check the documentation
- Try the example scripts

---

**Happy coding with SmartGlass AI Agent! 👓🤖**
