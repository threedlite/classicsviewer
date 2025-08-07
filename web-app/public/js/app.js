// Classics Viewer Web App
let currentLanguage = '<%= language %>';
let currentAuthor = null;
let currentWork = null;
let currentBook = null;
let currentPage = 1;
let linesPerPage = 30;
let viewMode = 'text'; // 'text' or 'translation'

// Cookie utility functions
function setCookie(name, value, days = 365) {
    const date = new Date();
    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
    const expires = "expires=" + date.toUTCString();
    document.cookie = name + "=" + JSON.stringify(value) + ";" + expires + ";path=/";
}

function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for(let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) {
            try {
                return JSON.parse(c.substring(nameEQ.length, c.length));
            } catch (e) {
                return null;
            }
        }
    }
    return null;
}

// Save reading position
function saveReadingPosition() {
    if (currentAuthor && currentWork && currentBook) {
        const position = {
            authorId: currentAuthor.id,
            authorName: currentAuthor.name,
            workId: currentWork.id,
            workTitle: currentWork.title,
            bookId: currentBook.id,
            bookTitle: currentBook.title,
            bookLabel: currentBook.label, // Add book label for multi-book works
            page: currentPage,
            viewMode: viewMode
        };
        setCookie('readingPosition', position);
    }
}

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    // First load authors
    loadAuthors().then(() => {
        // Then check for saved reading position
        const savedPosition = getCookie('readingPosition');
        if (savedPosition) {
            restoreReadingPosition(savedPosition);
        } else {
            // No saved position - set default to Homer's Iliad Book 1
            const defaultPosition = {
                authorId: 'tlg0012', // Homer
                authorName: 'Homer',
                workId: 'tlg0012.tlg001', // Iliad
                workTitle: 'Iliad',
                bookId: 'tlg0012.tlg001.1', // Book 1
                bookTitle: 'Iliad - Book 1',
                bookLabel: 'Book 1',
                page: 1,
                viewMode: 'text'
            };
            setCookie('readingPosition', defaultPosition);
            restoreReadingPosition(defaultPosition);
        }
    });
});


// Language selection
async function setLanguage(language) {
    try {
        const response = await fetch('/api/language', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ language })
        });
        
        if (response.ok) {
            window.location.reload();
        }
    } catch (error) {
        console.error('Error setting language:', error);
    }
}

// Load authors for the selected language
async function loadAuthors() {
    const language = document.getElementById('greekBtn').disabled ? 'greek' : 'latin';
    
    try {
        showLoading('authorList');
        const response = await fetch(`/api/authors/${language}`);
        const authors = await response.json();
        
        const authorList = document.getElementById('authorList');
        authorList.innerHTML = '';
        
        authors.forEach(author => {
            const item = document.createElement('a');
            item.href = '#';
            item.className = 'list-group-item list-group-item-action';
            item.textContent = author.name;
            item.dataset.authorId = author.id; // Store ID for restoration
            item.onclick = (e) => {
                e.preventDefault();
                selectAuthor(author.id, author.name, item);
            };
            authorList.appendChild(item);
        });
        
        return authors; // Return for restoration purposes
    } catch (error) {
        console.error('Error loading authors:', error);
        showError('authorList', 'Failed to load authors');
        return [];
    }
}

// Restore reading position
async function restoreReadingPosition(position) {
    try {
        // Set view mode
        viewMode = position.viewMode || 'text';
        if (viewMode === 'translation') {
            showTranslation();
        } else {
            showText();
        }
        
        // Find and click the author
        const authorItem = document.querySelector(`[data-author-id="${position.authorId}"]`);
        if (authorItem) {
            authorItem.click();
            
            // Wait for works to load
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Find and click the work
            const workItem = document.querySelector(`[data-work-id="${position.workId}"]`);
            if (workItem) {
                workItem.click();
                
                // Wait for books to load or text to load
                await new Promise(resolve => setTimeout(resolve, 800));
                
                // Check if we need to select a specific book (multi-book work)
                const bookItems = document.querySelectorAll('#contentArea .list-group-item');
                if (bookItems.length > 0) {
                    // This is a multi-book work, find the right book
                    let bookFound = false;
                    for (const bookItem of bookItems) {
                        // First try to match by book ID if available
                        if (bookItem.dataset.bookId === position.bookId) {
                            bookItem.click();
                            bookFound = true;
                            break;
                        }
                        // Fallback to matching by label/title
                        if (position.bookLabel && bookItem.textContent.includes(position.bookLabel)) {
                            bookItem.click();
                            bookFound = true;
                            break;
                        }
                    }
                    
                    if (bookFound) {
                        await new Promise(resolve => setTimeout(resolve, 300));
                    }
                }
                
                // Restore page
                if (position.page > 1) {
                    currentPage = position.page;
                    await loadPage();
                }
            }
        }
    } catch (error) {
        // Silently fail - don't show errors for invalid saved positions
        console.log('Could not restore saved position');
    }
}

// Select an author and load their works
async function selectAuthor(authorId, authorName, element) {
    // Update UI
    document.querySelectorAll('#authorList .list-group-item').forEach(item => {
        item.classList.remove('active');
    });
    element.classList.add('active');
    
    // Scroll the selected author into view
    element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    currentAuthor = { id: authorId, name: authorName };
    currentWork = null;
    currentBook = null;
    currentPage = 1;
    
    // Clear content area
    document.getElementById('contentArea').innerHTML = '<p class="text-muted text-center mt-5">Select a work to begin reading.</p>';
    document.getElementById('contentTitle').textContent = authorName;
    
    // Load works
    try {
        showLoading('bookList');
        const response = await fetch(`/api/works/${authorId}`);
        const works = await response.json();
        
        const bookList = document.getElementById('bookList');
        bookList.innerHTML = '';
        
        works.forEach(work => {
            const item = document.createElement('a');
            item.href = '#';
            item.className = 'list-group-item list-group-item-action';
            const title = work.title_english || work.title;
            item.textContent = title;
            item.dataset.workId = work.id; // Store ID for restoration
            item.onclick = (e) => {
                e.preventDefault();
                selectWork(work.id, title, item);
            };
            bookList.appendChild(item);
        });
    } catch (error) {
        console.error('Error loading works:', error);
        showError('bookList', 'Failed to load works');
    }
}

// Select a work and check if it has multiple books
async function selectWork(workId, workTitle, element) {
    // Update UI
    document.querySelectorAll('#bookList .list-group-item').forEach(item => {
        item.classList.remove('active');
    });
    element.classList.add('active');
    
    // Scroll the selected work into view
    element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    currentWork = { id: workId, title: workTitle };
    
    // Check if this work has multiple books
    try {
        const response = await fetch(`/api/books/${workId}`);
        const books = await response.json();
        
        if (books.length === 1) {
            // Single book, load it directly
            selectBook(books[0].id, workTitle, books[0].start_line, books[0].end_line);
        } else {
            // Multiple books, show book selection
            showBookSelection(books, workTitle);
        }
    } catch (error) {
        console.error('Error loading books:', error);
        showError('contentArea', 'Failed to load book information');
    }
}

// Show book selection for works with multiple books
function showBookSelection(books, workTitle) {
    const contentArea = document.getElementById('contentArea');
    contentArea.innerHTML = '<h5>Select a book:</h5><div class="list-group mt-3">';
    
    const listGroup = contentArea.querySelector('.list-group');
    books.forEach(book => {
        const item = document.createElement('a');
        item.href = '#';
        item.className = 'list-group-item list-group-item-action';
        item.textContent = book.label || `Book ${book.id}`;
        item.dataset.bookId = book.id; // Add data attribute for restoration
        item.onclick = (e) => {
            e.preventDefault();
            selectBook(book.id, `${workTitle} - ${book.label}`, book.start_line, book.end_line, book.label);
        };
        listGroup.appendChild(item);
    });
    
    contentArea.appendChild(listGroup);
}

// Select a book and load the first page
function selectBook(bookId, bookTitle, startLine, endLine, bookLabel = null) {
    currentBook = { 
        id: bookId, 
        title: bookTitle, 
        label: bookLabel || bookTitle, // Store label for multi-book works
        startLine: startLine, 
        endLine: endLine 
    };
    currentPage = 1;
    
    document.getElementById('contentTitle').textContent = `${currentAuthor.name} - ${bookTitle}`;
    
    // Enable navigation buttons
    document.getElementById('prevBtn').disabled = false;
    document.getElementById('nextBtn').disabled = false;
    
    // Load first page
    loadPage();
    
    // Save position
    setTimeout(() => saveReadingPosition(), 500);
}

// Load a page of text or translation
async function loadPage() {
    const startLine = (currentPage - 1) * linesPerPage + 1;
    const endLine = currentPage * linesPerPage;
    
    if (viewMode === 'text') {
        await loadText(startLine, endLine);
    } else {
        await loadTranslation(startLine, endLine);
    }
    
    // Update page info
    document.getElementById('pageInfo').textContent = `Page: ${currentPage}`;
    
    // Update navigation buttons
    document.getElementById('prevBtn').disabled = currentPage === 1;
    
    // Save position after loading
    saveReadingPosition();
}

// Load text
async function loadText(startLine, endLine) {
    try {
        showLoading('contentArea');
        const response = await fetch(`/api/text/${currentBook.id}/${startLine}/${endLine}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const lines = await response.json();
        
        const contentArea = document.getElementById('contentArea');
        contentArea.innerHTML = '';
        
        const language = document.getElementById('greekBtn').disabled ? 'greek' : 'latin';
        const textClass = language === 'greek' ? 'greek-text' : 'latin-text';
        
        lines.forEach(line => {
            const lineDiv = document.createElement('div');
            lineDiv.className = 'text-line';
            
            const lineNumber = document.createElement('span');
            lineNumber.className = 'line-number';
            lineNumber.textContent = line.line_number;
            
            const lineText = document.createElement('span');
            lineText.className = textClass;
            
            // Make words clickable
            lineText.innerHTML = makeWordsClickable(line.line_text, language);
            
            lineDiv.appendChild(lineNumber);
            lineDiv.appendChild(lineText);
            contentArea.appendChild(lineDiv);
        });
        
        // Disable next button if we got fewer lines than requested
        if (lines.length < linesPerPage) {
            document.getElementById('nextBtn').disabled = true;
        }
    } catch (error) {
        console.error('Error loading text:', error);
        showError('contentArea', 'Failed to load text');
    }
}

// Load translation
async function loadTranslation(startLine, endLine) {
    try {
        showLoading('contentArea');
        const response = await fetch(`/api/translation/${currentBook.id}/${startLine}/${endLine}`);
        const segments = await response.json();
        
        const contentArea = document.getElementById('contentArea');
        contentArea.innerHTML = '';
        
        if (segments.length === 0) {
            contentArea.innerHTML = '<p class="text-muted text-center mt-5">No translation available for this section.</p>';
            return;
        }
        
        segments.forEach(segment => {
            const segmentDiv = document.createElement('div');
            segmentDiv.className = 'translation-segment';
            
            const text = document.createElement('div');
            text.className = 'translation-text';
            text.textContent = segment.translation_text;
            
            const reference = document.createElement('div');
            reference.className = 'translation-reference';
            reference.textContent = `Lines ${segment.start_line}${segment.end_line ? '-' + segment.end_line : ''}`;
            
            segmentDiv.appendChild(text);
            segmentDiv.appendChild(reference);
            contentArea.appendChild(segmentDiv);
        });
    } catch (error) {
        console.error('Error loading translation:', error);
        showError('contentArea', 'Failed to load translation');
    }
}

// View mode switching
function showText() {
    viewMode = 'text';
    document.getElementById('textBtn').classList.add('active');
    document.getElementById('translationBtn').classList.remove('active');
    if (currentBook) {
        loadPage();
    }
}

function showTranslation() {
    viewMode = 'translation';
    document.getElementById('translationBtn').classList.add('active');
    document.getElementById('textBtn').classList.remove('active');
    if (currentBook) {
        loadPage();
    }
}

// Navigation
function loadPreviousPage() {
    if (currentPage > 1) {
        currentPage--;
        loadPage();
    }
}

function loadNextPage() {
    currentPage++;
    loadPage();
}

// Utility functions
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    element.innerHTML = '<div class="loading"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
}

function showError(elementId, message) {
    const element = document.getElementById(elementId);
    element.innerHTML = `<div class="alert alert-danger" role="alert">${message}</div>`;
}

// Set initial view mode
document.getElementById('textBtn').classList.add('active');

// Make words clickable
function makeWordsClickable(text, language) {
    // For Greek, also handle elision marks (ʼ U+02BC and ' regular apostrophe)
    const wordBoundary = language === 'greek' 
        ? /([\s\u2018\u2019\u201C\u201D.,;:!?\-\[\]()]+|[\u02BC']+$)/
        : /([\s\u2018\u2019\u201C\u201D.,;:!?\-\[\]()]+)/;
    
    const words = text.split(wordBoundary);
    
    return words.map((word, index) => {
        // Skip empty strings and pure punctuation
        if (!word || /^[\s\u2018\u2019\u201C\u201D.,;:!?\-\[\]()]+$/.test(word)) {
            return word;
        }
        
        // For Greek words ending with elision marks, create clickable word without the mark
        if (language === 'greek' && /[\u02BC']$/.test(word)) {
            const cleanWord = word.replace(/[\u02BC']+$/, '');
            const elisionMark = word.match(/[\u02BC']+$/)[0];
            return `<span class="clickable-word" onclick="lookupWord('${cleanWord.replace(/'/g, "\\'")}')">${cleanWord}</span>${elisionMark}`;
        }
        
        // Create clickable span for actual words
        return `<span class="clickable-word" onclick="lookupWord('${word.replace(/'/g, "\\'")}')">${word}</span>`;
    }).join('');
}

// Word lookup
async function lookupWord(word) {
    const language = document.getElementById('greekBtn').disabled ? 'greek' : 'latin';
    
    // Show panel
    const panel = document.getElementById('wordInfoPanel');
    panel.classList.add('show');
    
    // Update selected word
    document.getElementById('selectedWord').textContent = word;
    
    // Show loading states
    document.getElementById('dictionaryResults').innerHTML = '<div class="loading"><div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    document.getElementById('occurrencesResults').innerHTML = '<div class="loading"><div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    
    // Fetch dictionary entries
    fetchDictionary(word, language);
    
    // Fetch occurrences - search entire corpus, not just current book
    fetchOccurrences(word, null);
}

// Fetch dictionary entries
async function fetchDictionary(word, language) {
    try {
        const response = await fetch(`/api/dictionary/${encodeURIComponent(word)}/${language}`);
        const entries = await response.json();
        
        const resultsDiv = document.getElementById('dictionaryResults');
        
        if (entries.length === 0) {
            resultsDiv.innerHTML = '<p class="text-muted">No dictionary entries found.</p>';
            return;
        }
        
        resultsDiv.innerHTML = entries.map(entry => `
            <div class="dictionary-entry">
                <div class="dictionary-headword">${entry.headword}</div>
                <div class="dictionary-text">${entry.entry_plain || entry.entry_html || 'No definition available'}</div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error fetching dictionary:', error);
        document.getElementById('dictionaryResults').innerHTML = '<p class="text-danger">Error loading dictionary entries.</p>';
    }
}

// Fetch word occurrences
async function fetchOccurrences(word, bookId) {
    try {
        const language = document.getElementById('greekBtn').disabled ? 'greek' : 'latin';
        const url = bookId 
            ? `/api/occurrences/${encodeURIComponent(word)}/${bookId}?limit=500&language=${language}`
            : `/api/occurrences/${encodeURIComponent(word)}?limit=500&language=${language}`;
            
        const response = await fetch(url);
        const data = await response.json();
        
        const resultsDiv = document.getElementById('occurrencesResults');
        
        if (data.results.length === 0) {
            resultsDiv.innerHTML = '<p class="text-muted">No occurrences found.</p>';
            return;
        }
        
        const totalShown = data.results.reduce((sum, book) => sum + book.occurrences.length, 0);
        
        resultsDiv.innerHTML = `
            <p class="text-muted small mb-3">
                Found ${data.total_found} occurrences${data.total_found > totalShown ? ` (showing first ${totalShown})` : ''}. 
                <br>Word forms: ${data.word_forms.join(', ')}
            </p>
            <div style="max-height: 600px; overflow-y: auto;">
                ${data.results.map(book => `
                    <div class="mb-3">
                        <h6 class="text-primary">${book.title}</h6>
                        ${book.occurrences.map(occ => `
                            <div class="occurrence-item" onclick="goToLine('${book.book_id}', ${occ.line_number})">
                                <div class="occurrence-line-ref">Line ${occ.line_number}</div>
                                <div>${highlightWordInText(occ.line_text, occ.word, occ.word_position)}</div>
                            </div>
                        `).join('')}
                    </div>
                `).join('')}
            </div>
        `;
    } catch (error) {
        console.error('Error fetching occurrences:', error);
        document.getElementById('occurrencesResults').innerHTML = '<p class="text-danger">Error loading occurrences.</p>';
    }
}

// Highlight word in occurrence text
function highlightWordInText(text, word, position) {
    const words = text.split(/\s+/);
    if (position > 0 && position <= words.length) {
        words[position - 1] = `<span class="highlighted-word">${words[position - 1]}</span>`;
    }
    return words.join(' ');
}

// Navigate to specific line
function goToLine(bookId, lineNumber) {
    // TODO: Navigate to the specific book and line
    console.log(`Navigate to book ${bookId}, line ${lineNumber}`);
    closeWordPanel();
}

// Close word panel
function closeWordPanel() {
    document.getElementById('wordInfoPanel').classList.remove('show');
}