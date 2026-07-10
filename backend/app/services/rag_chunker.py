from typing import List

class RAGChunker:
    """Pure-Python text chunker that splits article body text into overlapping segments, targeting sentence boundaries."""

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 300) -> List[str]:
        """
        Splits text into overlapping chunks of character size, prioritizing sentence end punctuation.

        Args:
            text: Raw input string.
            chunk_size: Maximum character length per chunk.
            overlap: Character overlap between consecutive chunks.

        Returns:
            A list of text chunks.
        """
        if not text:
            return []
        
        text = text.strip()
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chunk_size
            if end >= text_len:
                chunks.append(text[start:])
                break

            # Search back within a window at the end of the chunk for sentence boundaries
            search_start = max(start, end - 150)
            boundary = -1
            for separator in [". ", "! ", "? ", ".\n", "!\n", "?\n"]:
                pos = text.rfind(separator, search_start, end)
                if pos != -1:
                    # Point after the punctuation space
                    pos_boundary = pos + len(separator)
                    if pos_boundary > boundary:
                        boundary = pos_boundary

            if boundary != -1:
                end = boundary

            chunks.append(text[start:end].strip())
            # Set next starting point back by overlap characters
            start = end - overlap
            
            # Safety checks to prevent infinite loops on long strings with no spacing
            if start < 0:
                start = 0
            if start >= end:
                start = end + 1

        return chunks
