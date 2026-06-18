# Sermon Audio Processor

A cross-platform Python + FFmpeg tool for automatically reprocessing spoken-word sermon audio into consistent podcast-style MP3 files.

## Current version

Version 1.2 changes:

- Supports `.mp3`, `.wav`, `.wave`, `.w64`, and `.wav64` originals.
- Always outputs `.mp3` files.
- MP3 originals keep their ID3 tags.
- WAV/W64 originals create MP3 outputs with blank ID3 tags, except for the optional processing comment.
- Scripts and Python code include expanded comments for future updates.
- Deployment instructions now cover macOS, Windows, and Linux.
- Added Linux setup/watch/batch helper scripts.
- Added `.gitignore` so source audio, processed audio, reports, and virtual environments do not get committed.
- Added VS Code + GitHub repository setup, deployment, and update instructions.

## What it does

Drop supported audio files into `inbox/` and the app will:

1. Wait until the file copy is finished.
2. Copy the original source file to `originals/`.
3. Analyze loudness using FFmpeg's two-pass `loudnorm` workflow.
4. Apply a gentle spoken-word cleanup chain:
   - 80 Hz high-pass filter
   - light mud reduction around 250 Hz
   - light intelligibility lift around 3.5 kHz
   - gentle compression
   - LUFS normalization
   - true-peak limiting
5. Write a processed MP3 to `output/`.
6. Preserve the filename stem:
   - `sermon.mp3` → `sermon.mp3`
   - `sermon.wav` → `sermon.mp3`
   - `sermon.w64` → `sermon.mp3`
7. Preserve ID3 tags only when the original was MP3.
8. Write a JSON report to `reports/`.
9. Copy failed files to `failed/`.

## Supported input and output formats

Supported input originals:

```text
.mp3
.wav
.wave
.w64
.wav64
```

Output format:

```text
.mp3 only
```

Metadata behavior:

```text
MP3 original  → copy ID3 tags to processed MP3
WAV original  → create blank ID3 tags unless processing comment is enabled
W64 original  → create blank ID3 tags unless processing comment is enabled
```

To disable the processing comment entirely, edit `config.yaml`:

```yaml
metadata:
  write_processing_comment: false
```

## Folder layout

```text
sermon_audio_processor/
  inbox/          Drop source audio files here
  output/         Finished processed MP3 files
  originals/      Safety copies of untouched source files
  failed/         Files copied here if processing fails
  processing/     Temporary working files
  reports/        Per-file JSON analysis/process reports
  config.yaml     Main tuning and folder configuration
```

## Recommended starting target

The included config uses a spoken-word podcast-style target:

```yaml
processing:
  target_lufs: -16.0
  true_peak_db: -1.5
  lra: 7.0
  mp3_bitrate: 192k
```

For spoken-word sermons, this is a good starting point. Test 10-20 sermons before processing the whole archive.

---

# macOS deployment

## macOS requirements

Install these first:

1. Python 3.10 or newer
2. FFmpeg, including ffprobe
3. Terminal access

Recommended install method:

```bash
brew install python ffmpeg
```

If you do not use Homebrew, install Python from python.org and FFmpeg from a trusted FFmpeg build source. After installing FFmpeg, open a new Terminal window and confirm:

```bash
ffmpeg -version
ffprobe -version
python3 --version
```

## macOS setup steps

Open Terminal and go to the project folder:

```bash
cd /path/to/sermon_audio_processor
```

Make the launch scripts executable:

```bash
chmod +x setup_mac.sh watch_mac.command batch_mac.command
```

Run setup:

```bash
./setup_mac.sh
```

Start continuous folder watching:

```bash
./watch_mac.command
```

Or process everything already in `inbox/` once:

```bash
./batch_mac.command
```

## macOS notes

- You can double-click `watch_mac.command` from Finder after setup.
- Keep the Terminal window open while watcher mode is running.
- Press `Ctrl+C` to stop watcher mode.
- If macOS blocks the command file because it was downloaded, right-click it, choose Open, then approve it.

---

# Windows deployment

## Windows requirements

Install these first:

1. Windows 10 or Windows 11
2. Python 3.10 or newer
3. FFmpeg, including ffprobe
4. PowerShell

Recommended install method from PowerShell:

```powershell
winget install Python.Python.3.12
winget install Gyan.FFmpeg
```

Close and reopen PowerShell after installing so PATH refreshes.

Confirm installation:

```powershell
python --version
ffmpeg -version
ffprobe -version
```

## Windows setup steps

Open PowerShell and go to the project folder:

```powershell
cd C:\Path\To\sermon_audio_processor
```

If script execution is blocked, allow it for this PowerShell session only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Run setup:

```powershell
.\setup_windows.ps1
```

Start continuous folder watching:

```powershell
.\watch_windows.bat
```

Or process everything already in `inbox\` once:

```powershell
.\batch_windows.bat
```

## Long-term Windows operation

For long-term use, run `watch_windows.bat` at login using Task Scheduler.

Suggested Task Scheduler settings:

```text
Trigger: At log on
Action: Start a program
Program/script: C:\Path\To\sermon_audio_processor\watch_windows.bat
Start in: C:\Path\To\sermon_audio_processor
Run only when user is logged on: recommended if you want to see the console
```

If you want it to run invisibly as a service later, use a service wrapper such as NSSM, but start with Task Scheduler first because it is easier to troubleshoot.

---

# Linux deployment

Linux is not required, but it is a good long-term option if you eventually want this running on a server.

## Ubuntu/Debian requirements

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg
```

Confirm installation:

```bash
python3 --version
ffmpeg -version
ffprobe -version
```

## Linux setup steps

Go to the project folder:

```bash
cd /path/to/sermon_audio_processor
```

Make helper scripts executable and run setup:

```bash
chmod +x setup_linux.sh watch_linux.sh batch_linux.sh
./setup_linux.sh
```

Run watcher mode:

```bash
./watch_linux.sh
```

Run batch mode:

```bash
./batch_linux.sh
```

Manual Linux setup also works:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m sermon_processor --check
```

## Optional Linux systemd service

Create a service file:

```bash
sudo nano /etc/systemd/system/sermon-audio-processor.service
```

Example service:

```ini
[Unit]
Description=Sermon Audio Processor
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/sermon_audio_processor
ExecStart=/opt/sermon_audio_processor/.venv/bin/python -m sermon_processor --watch
Restart=always
RestartSec=10
User=YOUR_LINUX_USER

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sermon-audio-processor
sudo systemctl start sermon-audio-processor
sudo systemctl status sermon-audio-processor
```

View logs:

```bash
journalctl -u sermon-audio-processor -f
```

---

# Manual commands

Check setup:

```bash
python -m sermon_processor --check
```

Process everything currently in `inbox/` once:

```bash
python -m sermon_processor --batch
```

Watch continuously:

```bash
python -m sermon_processor --watch
```

Process one file:

```bash
python -m sermon_processor --file "/path/to/sermon.wav"
```

On Windows, use the virtual environment Python directly if needed:

```powershell
.\.venv\Scripts\python.exe -m sermon_processor --file "C:\Path\To\sermon.wav"
```

On macOS/Linux, use:

```bash
source .venv/bin/activate
python -m sermon_processor --file "/path/to/sermon.wav"
```

---

# VS Code + GitHub setup

This section walks through getting the project into your own GitHub repository so you can track changes, move it between your Mac and Windows PC, and update it safely later.

## What to install first

Install these on your Mac now:

1. VS Code
2. Git
3. GitHub account
4. GitHub Pull Requests and Issues extension for VS Code, optional but helpful
5. Python extension for VS Code

On macOS with Homebrew:

```bash
brew install git
brew install --cask visual-studio-code
```

Confirm Git works:

```bash
git --version
```

## Sign in to GitHub from VS Code

1. Open VS Code.
2. Open the Command Palette:
   - macOS: `Cmd+Shift+P`
   - Windows/Linux: `Ctrl+Shift+P`
3. Search for `GitHub: Sign In`.
4. Follow the browser login prompts.
5. Return to VS Code after login completes.

If VS Code asks whether to allow GitHub authentication, approve it.

## Open this project in VS Code

1. Unzip the project.
2. Move the folder somewhere permanent, for example:

```text
~/Documents/Church/SermonAudioProcessor
```

3. In VS Code, choose `File > Open Folder...`.
4. Open the `sermon_audio_processor` folder.
5. When VS Code asks to trust the folder, choose `Trust` if this is your local project copy.

## Create the Git repository locally

In VS Code, open the integrated terminal:

```text
Terminal > New Terminal
```

Then run:

```bash
git init
git status
git add .
git commit -m "Initial sermon audio processor project"
```

The included `.gitignore` prevents sermon audio, processed files, originals, reports, temp files, and `.venv` from being uploaded to GitHub.

## Create a new GitHub repository from VS Code

1. Open the Source Control panel in VS Code.
2. Click `Publish Branch` or `Publish to GitHub`.
3. Choose a repository name, for example:

```text
sermon-audio-processor
```

4. Choose `Private` unless you intentionally want the code public.
5. Confirm publish.

After this, your code is backed up to GitHub. Your sermon audio files should not be uploaded because of `.gitignore`.

## Create a new GitHub repository from the GitHub website instead

You can also create the repo at GitHub first, then connect it manually.

1. Go to GitHub.
2. Click `New repository`.
3. Name it `sermon-audio-processor`.
4. Choose `Private`.
5. Do not initialize with a README, license, or `.gitignore` because this project already has those files.
6. Create the repository.
7. Copy the repository URL.
8. In the VS Code terminal, run:

```bash
git remote add origin https://github.com/YOUR_USERNAME/sermon-audio-processor.git
git branch -M main
git push -u origin main
```

## Normal update workflow

Any time you edit code, config defaults, or documentation:

```bash
git status
git add .
git commit -m "Describe what changed"
git push
```

Good commit examples:

```bash
git commit -m "Tune speech EQ preset"
git commit -m "Add Windows Task Scheduler notes"
git commit -m "Improve WAV metadata handling"
```

## Pull updates on your Windows PC later

On the Windows PC, install Python, FFmpeg, Git, and VS Code. Then clone your repository:

```powershell
cd C:\Church
git clone https://github.com/YOUR_USERNAME/sermon-audio-processor.git
cd sermon-audio-processor
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup_windows.ps1
```

To update the Windows copy later:

```powershell
cd C:\Church\sermon-audio-processor
git pull
.\setup_windows.ps1
```

Running setup again is safe. It refreshes the virtual environment dependencies and checks folders.

## Moving config between Mac and Windows

The default `config.yaml` uses relative folders, which works on all platforms. If you change to absolute paths, use OS-specific paths.

Mac example:

```yaml
folders:
  inbox: "/Users/jason/Sermons/To Process"
  output: "/Users/jason/Sermons/Processed"
```

Windows example:

```yaml
folders:
  inbox: "D:/Church/Sermons/To Process"
  output: "D:/Church/Sermons/Processed"
```

If you want separate Mac and Windows configs later, make copies such as:

```text
config.mac.yaml
config.windows.yaml
```

Then launch manually with:

```bash
python -m sermon_processor --config config.mac.yaml --watch
```

Or on Windows:

```powershell
.\.venv\Scripts\python.exe -m sermon_processor --config config.windows.yaml --watch
```

## Safe deployment checklist

Before processing the whole archive:

1. Put 10-20 representative sermons in `inbox/`.
2. Run batch mode.
3. Listen to the outputs on headphones, laptop speakers, and your normal playback system.
4. Adjust `config.yaml` if needed.
5. Commit the tuned config to GitHub.
6. Move the project to the Windows PC.
7. Run setup on Windows.
8. Configure Task Scheduler only after manual tests work.

## Updating the running Windows deployment

1. Stop the watcher window or scheduled task.
2. Pull updates:

```powershell
git pull
```

3. Refresh dependencies:

```powershell
.\setup_windows.ps1
```

4. Run a test batch with one or two files.
5. Restart the watcher or scheduled task.

---

---

# Configuration guide

Edit `config.yaml` to tune behavior.

## Folder paths

Relative paths are relative to the project folder:

```yaml
folders:
  inbox: inbox
  output: output
```

Absolute paths also work:

```yaml
folders:
  inbox: "D:/Church/Sermons/To Process"
  output: "D:/Church/Sermons/Processed"
```

On macOS/Linux:

```yaml
folders:
  inbox: "/Users/jason/Sermons/To Process"
  output: "/Users/jason/Sermons/Processed"
```

## Loudness

If sermons are too quiet:

```yaml
processing:
  target_lufs: -15.0
```

If sermons are too loud/aggressive:

```yaml
processing:
  target_lufs: -17.0
```

## EQ

If speech sounds boomy or muddy, increase the mud cut carefully:

```yaml
processing:
  mud_cut_db: -2.5
```

If speech sounds dull, increase presence carefully:

```yaml
processing:
  presence_boost_db: 2.0
```

If speech sounds harsh or piercing, reduce presence:

```yaml
processing:
  presence_boost_db: 0.5
```

## Compression

If volume jumps are still too distracting:

```yaml
processing:
  compressor_ratio: 2.8
```

If sermons sound too squeezed or unnatural:

```yaml
processing:
  compressor_ratio: 1.8
```

## Metadata

Copy ID3 tags from MP3 originals:

```yaml
metadata:
  preserve_id3_tags: true
```

Disable processing comment:

```yaml
metadata:
  write_processing_comment: false
```

---

# Important notes

- MP3 is lossy. Re-encoding can slightly reduce quality, so keep `originals/`.
- WAV/W64 originals are ideal sources because they avoid an extra lossy generation before final MP3 output.
- Do not repeatedly process already-processed MP3s unless needed.
- The EQ is intentionally conservative. Loudness consistency is the main win.
- For your first archive test, process 10-20 sermons from different years/sources and listen before running the full archive.

# Troubleshooting

## “ffmpeg was not found”

FFmpeg is not installed or is not in PATH.

macOS:

```bash
brew install ffmpeg
```

Windows:

```powershell
winget install Gyan.FFmpeg
```

Then close and reopen Terminal/PowerShell.

## “watchdog is not installed”

Run setup again, or manually install requirements inside the virtual environment:

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Windows:

```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
```

## Output file already exists

By default, existing outputs are skipped. Change this in `config.yaml` if needed:

```yaml
processing:
  skip_existing_outputs: false
```

When disabled, the app will create unique names such as `sermon_1.mp3` rather than overwrite existing files.
