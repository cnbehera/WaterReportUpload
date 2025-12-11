import requests
import json

def test_local_model(prompt="why is the sky blue"):
    """
    Test connection to local Ollama model
    """
    base_url = "http://127.0.0.1:11434"
    
    # First, check if the server is running
    try:
        health_response = requests.get(f"{base_url}/")
        print(f"✓ Server is running: {health_response.status_code}")
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server. Make sure Ollama is running.")
        return
    
    # List available models
    try:
        models_response = requests.get(f"{base_url}/api/tags")
        if models_response.status_code == 200:
            models = models_response.json()
            print(f"\n✓ Available models:")
            for model in models.get('models', []):
                print(f"  - {model['name']}")
            
            # Use the first available model or default to 'llama2'
            if models.get('models'):
                model_name = models['models'][0]['name']
            else:
                model_name = 'llama2'
                print(f"\n⚠ No models found, trying default: {model_name}")
        else:
            model_name = 'llama2'
            print(f"\n⚠ Could not list models, trying default: {model_name}")
    except Exception as e:
        print(f"✗ Error listing models: {e}")
        model_name = 'llama2'
    
    # Send the prompt
    print(f"\n📤 Sending prompt: '{prompt}'")
    print(f"🤖 Using model: {model_name}\n")
    
    try:
        # Ollama API endpoint for generation
        generate_url = f"{base_url}/api/generate"
        
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
        
        response = requests.post(generate_url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Response received:")
            print("-" * 50)
            print(result.get('response', 'No response text'))
            print("-" * 50)
            print(f"\n📊 Stats:")
            print(f"  - Total duration: {result.get('total_duration', 0) / 1e9:.2f}s")
            print(f"  - Load duration: {result.get('load_duration', 0) / 1e9:.2f}s")
            print(f"  - Eval count: {result.get('eval_count', 0)} tokens")
        else:
            print(f"✗ Error: {response.status_code}")
            print(response.text)
    
    except requests.exceptions.Timeout:
        print("✗ Request timed out. The model might be taking too long to respond.")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_local_model("why is the sky blue?")
