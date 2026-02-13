# Private Audio Transcriber (P-A-T)
Offline multilingual audio dictation and transcription for Mac. Powered by Whisper-MLX.

<br>

## Simple Self Customization

This app can be used in many languages and in many domains - medical, legal etc. The code is simple. Someone with only a basic knowledge of Python can modify the format of the output text to suit a particular use case. Only the run_transcription function (below) needs to be modified in the ```app.py``` file.

```
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

```

<br>

For example, you can add logic to fix errors that the transcriber routinely makes. Or, if the language is Spanish, you might want to highlight certain words in the text so they will be easier to see and quicker to edit.

```
elif language == 'es':
    dictation_keywords = ['coma', 'punto', 'nuevo párrafo']
    # ... apply same highlighting logic ...
```
