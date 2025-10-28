"""
SmartGlass AI Agent - Language Generation Module
Uses GPT-2 for generating contextual responses
"""

import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from typing import Optional, List


class GPT2TextGenerator:
    """
    Text generator using GPT-2 for generating natural language responses.
    Provides contextual and coherent text generation for smart glass interactions.
    """
    
    def __init__(self, model_name: str = "gpt2", device: Optional[str] = None):
        """
        Initialize GPT-2 text generator.
        
        Args:
            model_name: GPT-2 model name ('gpt2', 'gpt2-medium', 'gpt2-large', 'gpt2-xl')
                       'gpt2' (base) is recommended for smart glasses
            device: Device to run the model on ('cuda', 'cpu', or None for auto-detect)
        """
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Loading GPT-2 model '{model_name}' on device '{self.device}'...")
        
        self.tokenizer = GPT2Tokenizer.from_pretrained(model_name)
        self.model = GPT2LMHeadModel.from_pretrained(model_name).to(self.device)
        self.model_name = model_name
        
        # Set padding token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        print(f"GPT-2 model loaded successfully.")
    
    def generate_response(
        self,
        prompt: str,
        max_length: int = 100,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        num_return_sequences: int = 1,
        no_repeat_ngram_size: int = 2
    ) -> List[str]:
        """
        Generate text response based on prompt.
        
        Args:
            prompt: Input text prompt
            max_length: Maximum length of generated text
            temperature: Sampling temperature (higher = more random)
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            num_return_sequences: Number of responses to generate
            no_repeat_ngram_size: Prevent repetition of n-grams
        
        Returns:
            List of generated text responses
        """
        # Encode input
        inputs = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)
        
        # Set attention mask
        attention_mask = torch.ones(inputs.shape, dtype=torch.long, device=self.device)
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                inputs,
                attention_mask=attention_mask,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                num_return_sequences=num_return_sequences,
                no_repeat_ngram_size=no_repeat_ngram_size,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode outputs
        responses = []
        for output in outputs:
            text = self.tokenizer.decode(output, skip_special_tokens=True)
            # Remove the prompt from the response
            if text.startswith(prompt):
                text = text[len(prompt):].strip()
            responses.append(text)
        
        return responses
    
    def generate_smart_response(
        self,
        user_query: str,
        context: Optional[str] = None,
        response_type: str = "helpful"
    ) -> str:
        """
        Generate a smart, context-aware response.
        
        Args:
            user_query: User's question or command
            context: Additional context (e.g., "I see a red car")
            response_type: Type of response ('helpful', 'informative', 'conversational')
        
        Returns:
            Generated response text
        """
        # Construct prompt based on response type
        if response_type == "helpful":
            prompt_prefix = "User needs help. "
        elif response_type == "informative":
            prompt_prefix = "Provide information. "
        else:  # conversational
            prompt_prefix = ""
        
        # Add context if provided
        if context:
            prompt = f"{prompt_prefix}Context: {context}\nUser: {user_query}\nAssistant:"
        else:
            prompt = f"{prompt_prefix}User: {user_query}\nAssistant:"
        
        # Generate response
        responses = self.generate_response(
            prompt,
            max_length=len(prompt.split()) + 50,  # Adaptive length
            temperature=0.7,
            num_return_sequences=1
        )
        
        return responses[0]
    
    def summarize_text(self, text: str, max_length: int = 50) -> str:
        """
        Generate a summary of the given text.
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
        
        Returns:
            Summary text
        """
        prompt = f"Summarize the following text:\n{text}\nSummary:"
        responses = self.generate_response(
            prompt,
            max_length=len(prompt.split()) + max_length,
            temperature=0.5,
            num_return_sequences=1
        )
        return responses[0]
    
    def continue_conversation(
        self,
        conversation_history: List[str],
        max_history: int = 3
    ) -> str:
        """
        Continue a conversation based on history.
        
        Args:
            conversation_history: List of previous exchanges
            max_history: Maximum number of history items to use
        
        Returns:
            Generated response
        """
        # Use only recent history to avoid context overflow
        recent_history = conversation_history[-max_history:]
        prompt = "\n".join(recent_history) + "\nAssistant:"
        
        responses = self.generate_response(
            prompt,
            max_length=len(prompt.split()) + 40,
            temperature=0.7,
            num_return_sequences=1
        )
        
        return responses[0]
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "capabilities": ["text generation", "conversation", "summarization"]
        }


if __name__ == "__main__":
    # Example usage
    print("GPT-2 Text Generator - Example Usage")
    print("=" * 50)
    
    # Initialize generator
    generator = GPT2TextGenerator()
    
    # Display model info
    print("\nModel Information:")
    info = generator.get_model_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    print("\nReady to generate text!")
    print("\nUsage examples:")
    print("  # Generate response")
    print("  response = generator.generate_response('What is AI?')")
    print("\n  # Smart response with context")
    print("  response = generator.generate_smart_response('What do you see?', context='I see a red car')")
    print("\n  # Summarize text")
    print("  summary = generator.summarize_text('Long text here...')")
