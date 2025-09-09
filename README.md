# YOVA - Your Own Voice Assistant

YOVA is an open-source voice interface you can connect to any AI backend. It listens to speech, turns it into text, sends it to your API (ChatGPT, custom agents, n8n, or anything else), and then speaks back the response.

It's Raspberry Pi–based and ships with 3D-printed case files so you can assemble a compact, standalone device.

![YOVA](./docs/img/yova-simple.png)

The idea is simple: **you focus on building the brain**, YOVA handles the ears and mouth. It takes care of speech recognition, text-to-speech, and streaming so conversations feel natural and responsive.

By keeping latency low and supporting flexible endpoints (including REST and WebSockets), YOVA makes it easy to add real-time voice interaction to your applications without dealing with audio processing details.

```mermaid
graph TD
    subgraph Raspberry PI
        S[Speaker] --- Y[YOVA Core]
        M[Microphone] --- Y
    end

    Y <--> A[Your AI Assistant Backend API]
```

## What YOVA gives you:

- **Compact Pi device**: lightweight enough for edge devices, always ready to listen - a small device you can keep on your desk, in your room, or integrate into other projects. Comes with customizable 3D models so you can print your own version or tweak the design
- **Multi-language support**: supports multiple languages for speech recognition and text-to-speech, making it convenient for users worldwide
- **Real-time audio processing**: optimized for low latency voice interactions with streaming architecture
- **[Voice ID](docs/voice_id.md)**: biometric identification of users by voice for personalization and access control
- **[Audio post-processing](docs/audio_processing.md)**: advanced signal processing techniques including noise reduction, echo cancellation, and acoustic echo processing to significantly improve speech recognition accuracy
- **[Modular architecture](docs/architecture.md)**: add plugins, extensions, or connect other hardware without rewriting the core (e.g. add a camera, a screen, a speaker, a button, etc.)

## What YOVA doesn't provide:

- **Not a complete voice assistant**: YOVA is a building block for creating voice assistants, not a ready-to-use solution. The included OpenAI integration is just a simple example to get you started. You need to build your own backend connections to ChatGPT, Claude, custom agents, n8n workflows, or any other API - see [integration guide](docs/integration.md) for details. The real power lies in building your own custom assistant backend that fits your specific needs

## Efficient Processing Flow

YOVA is designed for low-latency voice interactions. Current performance metrics show:
- **Input latency**: ~60ms median from button press to recording start
- **Question processing**: ~500ms median from speech end to API call
- **Answer playback**: ~700ms median from API response to speech start (can be made to feel even better with proper UX strategies)

For detailed performance analysis, optimization strategies, and pro tips, see the [Performance Guide](docs/performance.md).

The following diagram illustrates how YOVA processes voice interactions from input to output, showing the streaming architecture that enables low-latency performance:

```mermaid
    graph LR
        VC[Voice<br/> Command] -->|stream| RS[Recording]
        RS -->|stream| AC[Audio<br/>Clean-Up]
        AC -->|stream| ASR[Speech<br/>Recognition]
        AC -->|audio| VID[Voice ID<br/>Identification]
        ASR -->|text| API[API<br/>Connector]
        VID -->|user| API

        API -->|text| B[Backend API]
        B[Backend API] -->|stream| API

        API -->|stream| TTS[Text-to-Speech]  
```


## Getting Started

To get started with YOVA, you'll need a Raspberry Pi 5 and a ReSpeaker 2-Mic HAT. The installation process involves:

1. **[Hardware Assembly](docs/install.md)** - 3D print the case and assemble the components
2. **[Software Installation](docs/install.md)** - Run the automated install script on your Raspberry Pi
3. **[Configuration](docs/config.md)** - Connect to built-in ChatGPT backend for testing
4. **[Integration](docs/integration.md)** - Connect to your custom backend API

For detailed step-by-step instructions, see the [Installation Guide](docs/install.md).
