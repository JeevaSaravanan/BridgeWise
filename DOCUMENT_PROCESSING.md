# Document Processing Implementation Guide

This document provides instructions for implementing real document processing libraries to replace the current simulation.

## Current Status ✅

The document processing feature is currently implemented with simulations that:
- ✅ Accept PDF, DOCX, and PPTX files
- ✅ Validate file types and sizes (max 10MB)
- ✅ Extract mock text content
- ✅ Analyze content for skills
- ✅ Generate summaries
- ✅ Show text previews
- ✅ Handle errors gracefully

## Implementation Steps for Real Processing

### 1. PDF Processing with pdf-parse

```bash
npm install pdf-parse
npm install @types/pdf-parse
```

Update `src/lib/documentProcessor.ts`:
```typescript
import * as pdfParse from 'pdf-parse';

static async processPDF(file: File): Promise<DocumentProcessingResult> {
  const buffer = await file.arrayBuffer();
  const data = await pdfParse(Buffer.from(buffer));
  
  return {
    text: data.text,
    metadata: {
      pageCount: data.numpages,
      wordCount: data.text.split(' ').length,
      fileType: 'PDF',
      processingTime: Date.now() - startTime
    }
  };
}
```

### 2. DOCX Processing with mammoth.js

```bash
npm install mammoth
npm install @types/mammoth
```

Update `src/lib/documentProcessor.ts`:
```typescript
import mammoth from 'mammoth';

static async processDOCX(file: File): Promise<DocumentProcessingResult> {
  const buffer = await file.arrayBuffer();
  const result = await mammoth.extractRawText({ buffer });
  
  return {
    text: result.value,
    metadata: {
      wordCount: result.value.split(' ').length,
      fileType: 'DOCX',
      processingTime: Date.now() - startTime
    }
  };
}
```

### 3. PPTX Processing

For PPTX, you can use libraries like:
- `pptx2json` - Convert PPTX to JSON
- `officegen` - Generate and parse Office documents
- Custom implementation using JSZip

```bash
npm install jszip
npm install xml2js
```

Example implementation:
```typescript
import JSZip from 'jszip';
import { parseString } from 'xml2js';

static async processPPTX(file: File): Promise<DocumentProcessingResult> {
  const zip = await JSZip.loadAsync(file);
  const slides = [];
  
  // Extract text from slide XML files
  for (const filename in zip.files) {
    if (filename.startsWith('ppt/slides/slide') && filename.endsWith('.xml')) {
      const slideXml = await zip.files[filename].async('string');
      const text = await this.extractTextFromSlideXml(slideXml);
      slides.push(text);
    }
  }
  
  const combinedText = slides.join('\n\n');
  
  return {
    text: combinedText,
    metadata: {
      wordCount: combinedText.split(' ').length,
      fileType: 'PPTX',
      processingTime: Date.now() - startTime
    }
  };
}
```

## Error Handling

Implement robust error handling for:
- Corrupted files
- Password-protected documents
- Large files that timeout
- Unsupported file formats
- Network issues during processing

```typescript
try {
  const result = await DocumentProcessor.processDocument(file);
  return result;
} catch (error) {
  if (error.message.includes('password')) {
    throw new Error('Password-protected documents are not supported');
  } else if (error.message.includes('corrupted')) {
    throw new Error('File appears to be corrupted or invalid');
  } else {
    throw new Error(`Processing failed: ${error.message}`);
  }
}
```

## Performance Optimization

For large files:
1. Implement streaming where possible
2. Add progress callbacks for long operations
3. Use Web Workers for heavy processing
4. Implement file size limits
5. Add caching for processed documents

## Security Considerations

1. Validate file headers, not just extensions
2. Sanitize extracted text content
3. Limit processing time with timeouts
4. Scan for malicious content
5. Use Content Security Policy

## Testing

Create test files:
- `test-files/sample.pdf` - Multi-page PDF with text
- `test-files/sample.docx` - Word document with formatting
- `test-files/sample.pptx` - PowerPoint with multiple slides
- `test-files/corrupted.pdf` - Invalid file for error testing

## Future Enhancements

1. **OCR Support**: Add optical character recognition for scanned documents
2. **Image Extraction**: Extract and analyze images from documents
3. **Table Extraction**: Parse tables and structured data
4. **Metadata Extraction**: Extract author, creation date, etc.
5. **Language Detection**: Identify document language
6. **Content Categorization**: Automatically categorize document types
