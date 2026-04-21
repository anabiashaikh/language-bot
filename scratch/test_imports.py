import sys
print("Python version:", sys.version)
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    print("langchain_text_splitters imported successfully")
except Exception as e:
    print("Error importing langchain_text_splitters:", e)

try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    print("langchain_community.embeddings imported successfully")
except Exception as e:
    print("Error importing langchain_community.embeddings:", e)
