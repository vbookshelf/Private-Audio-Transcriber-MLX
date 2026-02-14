#----------------------
# Private Audio Transcriber
# Creator: vbookshelf
# GitHub: https://github.com/vbookshelf/Private-Audio-Transcriber-MLX
# License: MIT
# Version: 1.0 (Whisper Integration)
#----------------------

import os
import sys
import socket
from flask import Flask, render_template_string, request, jsonify
import re

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"


import tempfile
import webbrowser
from threading import Timer
import mlx_whisper



# --- Transcription ---
def run_transcription(audio_path):
    """
    Transcribes audio using the mlx_whisper model and highlights dictation keywords.
    """
    result = mlx_whisper.transcribe(
        audio_path,
        # Make sure this points to your local model directory
        path_or_hf_repo="models/whisper-turbo-mlx"
    )
	
    text = result['text'].strip()
    language = result['language']
	
	
    if language == 'en':
	
	    # Keywords to be highlighted. This is case-insensitive.
	    dictation_keywords = [
	        'comma',
	        'period',
	        'colon',
	        'new paragraph',
	        'end of note'
	    ]
	
	    highlighted_text = text
	    for keyword in dictation_keywords:
	        # Use re.sub with a lambda function to wrap the found word
	        # while preserving its original casing (e.g., "Comma" becomes "<Comma>").
	        # Word boundaries (\b) ensure we don't highlight parts of other words.
	        pattern = r'\b(' + re.escape(keyword) + r')\b'
	        highlighted_text = re.sub(
	            pattern,
	            lambda match: f"<{match.group(1)}>",
	            highlighted_text,
	            flags=re.IGNORECASE
	        )
	
	    return highlighted_text
		
    else:
        return text
	
	

# --- Flask Application ---
app = Flask(__name__)

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024 # 100MB

# --- Security Features ---

@app.after_request
def add_security_headers(response):
    """
    Adds security headers to each response.
    """
    # Updated CSP to allow inline styles, scripts, and blob URLs for audio playback.
    csp = (
        "default-src 'self';"
        "style-src 'self' 'unsafe-inline';"
        "script-src 'self' 'unsafe-inline';"
        "media-src 'self' blob:;"
    )
    response.headers['Content-Security-Policy'] = csp
    # Prevent the app from being embedded in an iframe
    response.headers['X-Frame-Options'] = 'DENY'
    return response

def check_host(host_to_check):
    """
    Checks if the server is configured to listen only on a local address.
    Aborts if a non-local host is provided.
    """
    if host_to_check not in ("127.0.0.1", "localhost"):
        print(f"ERROR: Attempting to bind to a non-local host '{host_to_check}'. Aborting for security reasons.")
        sys.exit(1)
    print(f"Host verification passed. Server will bind to {host_to_check}.")


HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PAT</title>
	
	<link rel="shortcut icon" type="image/png" href="static/icon.png">
	
    <style>
        :root {
            --primary: #2563eb; --primary-hover: #1d4ed8; --bg: #f1f5f9;
            --card: #ffffff; --text: #1e293b; --text-light: #64748b;
            --danger: #ef4444; --border: #e2e8f0; --edit-bg: #fffcf0;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, sans-serif; }
        body { background-color: var(--bg); color: var(--text); height: 100vh; display: flex; overflow: hidden; }
        .left-col { width: 350px; background: #1f2937; border-right: 1px solid #374151; color: #d1d5db; display: flex; flex-direction: column; align-items: center; justify-content: flex-start; padding: 2rem; text-align: center; box-shadow: 4px 0 10px rgba(0,0,0,0.2); }
        .right-col { flex: 1; padding: 0.5rem; overflow-y: auto; background: var(--bg); display: flex; flex-direction: column; }
        
        .mic-container { position: relative; display: flex; flex-direction: column; align-items: center; width: 100%;}
        .mic-btn { width: 100px; height: 100px; border-radius: 50%; border: none; background: var(--primary); color: white; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.4); margin-bottom: 1rem; }
        .mic-btn.recording { background: var(--danger); transform: scale(1.1); box-shadow: 0 0 0 15px rgba(239, 68, 68, 0.2); animation: pulse-ring 1.5s infinite; }
        @keyframes pulse-ring { 0% { box-shadow: 0 0 0 0px rgba(239, 68, 68, 0.4); } 100% { box-shadow: 0 0 0 20px rgba(239, 68, 68, 0); } }
        .hotkey-hint { padding: 0.4rem 0.8rem; background: #374151; border: 1px solid #4b5563; border-radius: 4px; font-size: 0.75rem; color: #d1d5db; display: inline-flex; align-items: center; gap: 0.5rem; }
        kbd { background: #4b5563; border: 1px solid #6b7280; color: #e5e7eb; border-radius: 3px; padding: 1px 6px; font-family: monospace; box-shadow: 0 1px 0 rgba(0,0,0,0.2); }
        
        .separator { font-weight: 600; color: #6b7280; margin: 1.5rem 0; width: 100%; text-align: center; border-bottom: 1px solid #374151; line-height: 0.1em; }
        .separator span { background: #1f2937; padding: 0 10px; }

        #drop-zone { width: 100%; border: 2px dashed #4b5563; border-radius: 8px; padding: 1.5rem; text-align: center; cursor: pointer; transition: background-color 0.2s, border-color 0.2s; }
        #drop-zone.drag-over { background-color: #374151; border-color: var(--primary); }
        #drop-zone p { color: #9ca3af; margin-top: 0.5rem; font-size: 0.8rem; }
        #file-input { display: none; }
        
        #file-list-container { width: 100%; margin-top: 1rem; text-align: left; }
        #file-list-container h3 { font-size: 0.8rem; text-transform: uppercase; color: #9ca3af; margin-bottom: 0.5rem; }
        #file-list { list-style: none; max-height: 150px; overflow-y: auto; background: #111827; border: 1px solid #374151; border-radius: 4px; padding: 0.5rem; }
        #file-list li { font-size: 0.85rem; padding: 0.4rem 0.6rem; border-bottom: 1px solid #374151; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

        .status-text { font-weight: 600; font-size: 0.9rem; color: #9ca3af; height: 20px; margin-top: 1rem; }
        .loader { display: none; margin: 1rem auto 0 auto; border: 3px solid #f3f3f3; border-top: 3px solid var(--primary); border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

        .right-header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 1rem; margin-bottom: 1.5rem; border-bottom: 1px solid var(--border); max-width: 800px; width: 100%; margin-left: auto; margin-right: auto; }
        .header-note { font-style: italic; font-size: 0.9rem; color: var(--text-light); }
        .header-actions { display: flex; gap: 1rem; }
        
        .chart-paper { background: white; padding: 2rem 3rem; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); max-width: 800px; margin: 0 auto; width: 100%; flex-grow: 1; }
        .transcription-group { margin-bottom: 2.5rem; }
        .field-label { font-size: 0.75rem; font-weight: 700; color: var(--primary); text-transform: uppercase; margin-bottom: 0.5rem; display: block; }
        
        .text-area-container { position: relative; width: 100%; }
        .copy-btn {
            position: absolute; top: 8px; right: 8px; background: white; border: 1px solid var(--border); border-radius: 4px;
            padding: 5px; cursor: pointer; z-index: 5; display: flex; align-items: center; justify-content: center;
            transition: all 0.2s; opacity: 0.6;
        }
        .copy-btn:hover { opacity: 1; background: #f8fafc; border-color: var(--primary); }
        .copy-btn svg { width: 16px; height: 16px; color: var(--text-light); }

        .transcription-area { width: 100%; min-height: 250px; padding: 0.75rem; padding-right: 2.5rem; border-radius: 0.4rem; border: 1px solid #e2e8f0; line-height: 1.8; color: var(--text); outline: none; transition: all 0.2s; background: #fafafa; resize: vertical; font-size: 1rem; transition: height 0.2s ease-in-out;}
		
        .transcription-area:focus { background: var(--edit-bg); border-color: #fbbf24; box-shadow: 0 0 0 2px rgba(251, 191, 36, 0.3); }
        .btn-small { padding: 0.5rem 1rem; font-size: 0.85rem; border-radius: 4px; border: 1px solid var(--border); background: white; cursor: pointer; display: flex; align-items: center; gap: 0.4rem; }
    </style>
</head>
<body>
    <aside class="left-col">
        <div class="mic-container">
            <button id="micBtn" class="mic-btn">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
            </button>
            <div class="hotkey-hint"><kbd>Space</kbd> Start / Stop Recording</div>
        </div>

        <div class="separator"><span>OR</span></div>
        
        <label for="file-input" id="drop-zone">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
            <p>Click or drag audio files.<br>wav - mp3 - m4a</p>
        </label>
        <input type="file" id="file-input" multiple accept="audio/*">
        
        <div id="file-list-container" style="display: none;">
            <h3>Processed Files</h3>
            <ul id="file-list"></ul>
        </div>
        
        <div id="statusText" class="status-text">Ready</div>
        <div id="loader" class="loader"></div>
        </aside>

    <main class="right-col">
        <div class="right-header">
            <span class="header-note">Each transcription can be edited</span>
            <div class="header-actions">
                <button class="btn-small" onclick="clearSession()">Reset Form</button>
            </div>
        </div>
        <div class="chart-paper">
            <div id="results-container"></div>
        </div>
    </main>

    <script>
        const micBtn = document.getElementById('micBtn');
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        const fileListContainer = document.getElementById('file-list-container');
        const fileList = document.getElementById('file-list');
        const statusText = document.getElementById('statusText');
        const loader = document.getElementById('loader');
        const resultsContainer = document.getElementById('results-container');

        const COPY_ICON = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
        const CHECK_ICON = `<svg viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;

        let isRecording = false;
        let mediaRecorder = null;
        let audioChunks = [];
        let audioBlob = null;

        // Load data on start
        window.addEventListener('DOMContentLoaded', () => {
            const savedData = sessionStorage.getItem('transcriptions');
            if (savedData) {
                const transcriptions = JSON.parse(savedData);
                transcriptions.reverse().forEach(item => {
                    displayTranscription(item.fileName, item.text, null, item.id);
                });
            }
        });

        function saveToSession() {
            const groups = document.querySelectorAll('.transcription-group');
            const dataToSave = Array.from(groups).map(group => {
                return {
                    id: group.dataset.id,
                    fileName: group.querySelector('.field-label').textContent,
                    text: group.querySelector('textarea').value
                };
            });
            sessionStorage.setItem('transcriptions', JSON.stringify(dataToSave));
        }

        function clearSession() {
            if(confirm("Are you sure you want to clear all transcriptions?")) {
                sessionStorage.removeItem('transcriptions');
                location.reload();
            }
        }

        window.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        window.addEventListener('dragleave', (e) => {
            if (!e.relatedTarget) {
                dropZone.classList.remove('drag-over');
            }
        });

        window.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            handleFiles(e.dataTransfer.files);
        });

        fileInput.addEventListener('change', () => handleFiles(fileInput.files));

        async function handleFiles(files) {
            if (isRecording) {
                alert("Please stop the recording before uploading files.");
                return;
            }
            if (files.length === 0) return;

            fileListContainer.style.display = 'block';
            loader.style.display = 'block';
            
            for (const file of [...files]) {
                const li = document.createElement('li');
                li.textContent = `Processing: ${file.name}...`;
                fileList.appendChild(li);
                
                statusText.innerText = `Transcribing ${file.name}...`;
                await processSingleAudio(file, file.name, file);
                
                li.textContent = `✓ ${file.name}`;
            }
            
            statusText.innerText = "Processing complete.";
            loader.style.display = 'none';
            fileInput.value = ''; 
        }

        async function toggleRecording() {
            if (isRecording) {
                // Clicking Stop triggers the transcription immediately
                mediaRecorder.stop();
                isRecording = false;
                micBtn.classList.remove('recording');
            } else {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    fileInput.value = ''; 

                    isRecording = true;
                    micBtn.classList.add('recording');
                    statusText.innerText = "RECORDING LIVE";
                    audioChunks = [];
                    mediaRecorder = new MediaRecorder(stream);
                    mediaRecorder.ondataavailable = event => audioChunks.push(event.data);
                    
                    mediaRecorder.onstop = async () => {
                        audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                        stream.getTracks().forEach(track => track.stop());
                        
                        // AUTO-PROCESS START
                        loader.style.display = 'block';
                        statusText.innerText = "Transcribing recording...";
                        await processSingleAudio(audioBlob, "Live Recording", audioBlob);
                        
                        statusText.innerText = "Ready for next note";
                        loader.style.display = 'none';
                    };
                    mediaRecorder.start();
                } catch (e) {
                    alert("Microphone access denied.");
                }
            }
        }
        
        micBtn.addEventListener('click', toggleRecording);
        
        window.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
                toggleRecording();
            }
        });

        async function processSingleAudio(audioSource, sourceName, fileObject) {
		    const formData = new FormData();
		    formData.append("audio_file", audioSource, `${sourceName}.webm`);
		    
		    try {
		        // Consolidate into ONE fetch call
		        const response = await fetch("/transcribe", { 
		            method: "POST", 
		            body: formData,
		            headers: { "X-Requested-With": "MedicalApp" } 
		        });
		
		        const data = await response.json();
		        displayTranscription(sourceName, data.transcription || 'Could not transcribe.', fileObject);
		    } catch (error) {
		        displayTranscription(sourceName, 'ERROR: Transcription failed.', fileObject);
		    }
		}
		
		
		

        function displayTranscription(fileName, transcriptionText, fileObject = null, existingId = null) {
            const group = document.createElement('div');
            group.className = 'transcription-group';
            group.dataset.id = existingId || Date.now() + Math.random().toString(36).substr(2, 9);
            
            const label = document.createElement('span');
            label.className = 'field-label';
            label.textContent = fileName;
            group.appendChild(label);

            if (fileObject) {
                const audioPlayer = document.createElement('audio');
                audioPlayer.controls = true;
                audioPlayer.src = URL.createObjectURL(fileObject);
                audioPlayer.style.width = '100%';
                audioPlayer.style.marginBottom = '0.75rem';
                group.appendChild(audioPlayer);
            }
            
            const container = document.createElement('div');
            container.className = 'text-area-container';

            const copyBtn = document.createElement('button');
            copyBtn.className = 'copy-btn';
            copyBtn.innerHTML = COPY_ICON;
            copyBtn.title = "Copy to clipboard";
            
            const textarea = document.createElement('textarea');
            textarea.className = 'transcription-area';
            textarea.value = transcriptionText;

            textarea.oninput = () => saveToSession();

            // New functionality to expand and collapse the textarea
            textarea.onfocus = () => {
                textarea.style.height = 'auto'; // Reset height to auto to get the correct scrollHeight
                textarea.style.height = (textarea.scrollHeight) + 'px';
            };

            textarea.onblur = () => {
                textarea.style.height = '250px'; // Reset to the original min-height
            };


            copyBtn.onclick = () => {
                navigator.clipboard.writeText(textarea.value);
                copyBtn.innerHTML = CHECK_ICON;
                setTimeout(() => { copyBtn.innerHTML = COPY_ICON; }, 2000);
            };

            container.appendChild(copyBtn);
            container.appendChild(textarea);
            group.appendChild(container);
            resultsContainer.prepend(group);
            
            saveToSession();
        }
		
		
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)
	
	
# --- CHANGED: Simplified Endpoint (No Conversion) ---
@app.route("/transcribe", methods=["POST"])
def transcribe():
	
    # 1. CSRF Security Check: Verify the custom header
    if request.headers.get("X-Requested-With") != "MedicalApp":
        return jsonify({"error": "Unauthorized request source"}), 403
	
    if 'audio_file' not in request.files:
        return jsonify({"error": "No audio file"}), 400

    audio_file = request.files['audio_file']
    
    # 1. Create local project directory for transparency
    upload_dir = os.path.join(os.getcwd(), "temp_user_uploads")
    os.makedirs(upload_dir, exist_ok=True)

    # Validation logic
    MAX_FILE_SIZE = 100 * 1024 * 1024 
    if audio_file.content_length and audio_file.content_length > MAX_FILE_SIZE:
        return jsonify({"error": "File too large"}), 413
        
    original_suffix = os.path.splitext(audio_file.filename)[1] if '.' in audio_file.filename else '.webm'
    allowed_extensions = {'.wav', '.mp3', '.m4a', '.webm'}
    if original_suffix.lower() not in allowed_extensions:
        return jsonify({"error": "Invalid file type"}), 400
    
    temp_audio_path = None
    try:
        # 2. Save uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(dir=upload_dir, delete=False, suffix=original_suffix) as temp_audio:
            audio_file.save(temp_audio.name)
            temp_audio_path = temp_audio.name

        # Directly transcribe the saved file
        transcribed_text = run_transcription(temp_audio_path)
        return jsonify({"transcription": transcribed_text})
    
    except Exception as e:
        # Log the detailed error to the terminal/console
        print(f"--- TRANSCRIPTION ERROR ---\n{str(e)}\n---------------------------")
        # Return a generic, safe message to the browser
        return jsonify({"error": "Transcription failed. Please check the console logs."}), 500
        
    finally:
        # 3. Explicitly clean up the single temporary file
        if temp_audio_path and os.path.exists(temp_audio_path): 
            os.remove(temp_audio_path)
			

def open_browser(host, port):
      webbrowser.open_new(f'http://{host}:{port}')
	  
	  

if __name__ == "__main__":
	
    # Define host and port for the server
    host = "127.0.0.1"
    port = 5001

    # Perform the security check before starting the server
    check_host(host)
    
    # Open the UI in a new tab automatically
    Timer(1, lambda: open_browser(host, port)).start()
    
    # Run the Flask application
    app.run(host=host, port=port, debug=False)
	
	