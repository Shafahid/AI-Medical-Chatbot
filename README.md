# AI-Medical-Chatbot

## Features

- **Medical Question Answering**: The chatbot can respond to medical queries based on a pre-trained model from HuggingFace.
- **Real-time Conversation**: Using Streamlit, users can interact with the chatbot in real-time.
- **Vector Search**: Using Faiss CPU, the chatbot performs efficient similarity searches to retrieve relevant answers from a database of medical information.
- **Simple Setup**: This guide is designed for beginners with minimal setup and configuration.

## Tools and Technologies Used

- **HuggingFace Transformers**: For pre-trained models and embeddings.
- **Faiss CPU**: For efficient vector storage and similarity search.
- **Streamlit**: For building the conversational interface.
- **Mistral**: For natural language understanding.

## Installation

Follow these steps to set up the Medical Chatbot:

### Prerequisites

- Python 3.7+
- Installed dependencies: HuggingFace, Faiss, Streamlit, Mistral

### 1. Clone the Repository

Start by cloning the repository:

```bash
git clone https://github.com/yourusername/medical-chatbot.git
cd medical-chatbot
