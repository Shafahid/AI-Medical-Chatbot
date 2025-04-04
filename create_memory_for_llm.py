from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

#Step 1: Load raw PDFs
DATA_PATH = "data/" 
def load_pdf_files(data):
    loader = DirectoryLoader(
        data,
        glob='*.pdf',
        loader_cls=PyPDFLoader
    )
    documents = loader.load()
    return documents

documents = load_pdf_files(data=DATA_PATH)
print(len(documents))

# Step 2: Create Chunks
def create_chunks(extracted_data):
    text_splitter=RecursiveCharacterTextSplitter(chunk_size=500,chunk_overlap=50)
    text_chunks=text_splitter.split_documents(extracted_data)
    return text_chunks


text_chinks = create_chunks(documents)

#Step 3: Create Vector Embeddings
def get_embedding_model():
    embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return embedding_model
    
embedding_model = get_embedding_model()

# Step 4: Store embeddings in Vector DB
DB_FAISS_PATH="vectorstore/db_faiss"    # FAISS stores data locally
db=FAISS.from_documents
DB_FAISS_PATH = "vectorstore/db_faiss"
db = FAISS.from_documents(text_chinks,embedding_model)
db.save_local(DB_FAISS_PATH)
