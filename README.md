# 🎸 Capo | Unlock the Music

**Capo** is a cross-platform, open-source chord detection tool designed for musicians. It analyzes audio files to detect harmony in real-time, allowing you to learn songs, practice riffs, and jam along seamlessly.

Created as a modern, Linux-friendly alternative to legacy tools like *Riffstation*, Capo runs natively on **Windows, macOS and Linux**.

![Capo Main Interface](assets/screenshot.png)


## 🚀 Features

* **🔍 AI-Powered Chord Detection:** Uses audio signal processing (Librosa) to analyze MP3/WAV files and predict chords.
* **🎛️ Performance Controls:**
    * **Tempo Control:** Slow down fast solos without changing the pitch.
    * **Key Shift:** Transpose the song up or down to match your vocal range or tuning.
    * **Virtual Capo:** Apply a capo offset to see chords relative to your guitar's capo position.
* **🎹 Dual Chord Modes:**
    * **Beginner:** Simplified Triads (Major/Minor) for easy playing.
    * **Advanced:** 7ths and extended chords for accurate harmony.
* **🌊 Interactive Waveform:** Visual navigation of the track with playhead scrubbing and zooming.
* **🎨 Custom UI:** A beautiful, distraction-free wood-textured interface built with PyQt6.
* **💻 Cross-Platform:** Standalone executables available for Windows, Mac, and Ubuntu/Linux.

## 📥 Download & Install

You don't need Python installed to use Capo! Just download the app for your OS from the releases page.

👉 **[Download the Latest Release Here](https://github.com/rickraph/Capo/releases)**

1.  **Windows:** Download `Capo-Windows.zip`, extract, and run `Capo.exe`.
2.  **Linux:** Download `Capo-Ubuntu.zip`, extract, and run the binary.
3.  **Mac:** Download `Capo-macOS.zip`, extract, and run the app.

## 🛠️ Built With

* **[Python 3](https://www.python.org/)** - Core logic.
* **[PyQt6](https://pypi.org/project/PyQt6/)** - The Graphical User Interface (GUI).
* **[Librosa](https://librosa.org/)** - Audio analysis and feature extraction.
* **[NumPy](https://numpy.org/)** - Mathematical operations.
* **GitHub Actions** - Automated CI/CD pipeline for building cross-platform binaries.

## 👨‍💻 Running from Source

If you are a developer and want to modify or run the code directly:

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/rickraph/Capo.git](https://github.com/rickraph/Capo.git)
    cd Capo
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the App:**
    ```bash
    python main.py
    ```

## 📖 The Story Behind Capo

I used to rely heavily on *Riffstation* on Windows to figure out chords for my guitar and keyboard sessions. When I switched my daily driver to **Ubuntu Linux**, I realized my favorite tool wasn't supported.

Instead of switching back, I decided to build my own solution. Capo was born out of necessity—a tool built by a musician, for musicians, that respects your choice of Operating System.

*Special thanks to @Sandesh Sunny for suggesting the name "Capo"!*

*Made with ❤️ and Python.*