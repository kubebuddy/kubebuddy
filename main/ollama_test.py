import ollama
def test_ollama():
    try:
        response = ollama.chat(
            model="llama3",   # you can replace with mistral, codellama, etc.
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, how are you?"}
            ]
        )
        print(response)  # Print full response for debugging
        print("\n--- Model Reply ---\n")
        print(response['message']['content'])
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_ollama()
