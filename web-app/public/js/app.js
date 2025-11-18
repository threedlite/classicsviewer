// Classics Viewer Web App
// currentLanguage is set by inline script in HTML
let currentAuthor = null;
let currentWork = null;
let currentBook = null;
let currentPage = 1;
let linesPerPage = 30;
let viewMode = 'text'; // 'text', 'translation', or 'interlinear'
let availableTranslators = [];
let selectedTranslator = null;
let interlinearData = null; // Cache interlinear data for the current work

// Get current selected language
function getCurrentLanguage() {
    return currentLanguage;
}

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

// Store all authors and works for filtering
let allAuthors = [];
let allWorks = [];
let filteredAuthors = [];
let filteredWorks = [];

// Load authors for the selected language
async function loadAuthors() {
    const language = getCurrentLanguage();

    try {
        showLoading('authorList');
        const response = await fetch(`/api/authors/${language}`);
        const authors = await response.json();

        // Store all authors for filtering
        allAuthors = authors;
        filteredAuthors = [...authors];

        // Display authors
        displayAuthors();

        // Set up filter listeners
        setupAuthorFilters();

        return authors; // Return for restoration purposes
    } catch (error) {
        console.error('Error loading authors:', error);
        showError('authorList', 'Failed to load authors');
        return [];
    }
}

// Display filtered authors
function displayAuthors() {
    const authorList = document.getElementById('authorList');
    authorList.innerHTML = '';

    filteredAuthors.forEach(author => {
        const item = document.createElement('a');
        item.href = '#';
        item.className = 'list-group-item list-group-item-action';

        // Format display name: show both Devanagari and English for Sanskrit
        let displayName = author.name;
        if (author.name_alt) {
            displayName = `${author.name} <span class="text-muted small">(${author.name_alt})</span>`;
        }

        // Bold text for authors with translations (like Android)
        if (author.has_translated_works) {
            item.innerHTML = `<strong>${displayName}</strong>`;
        } else {
            item.innerHTML = displayName;
        }

        item.dataset.authorId = author.id; // Store ID for restoration
        item.onclick = (e) => {
            e.preventDefault();
            selectAuthor(author.id, author.name, item);
        };
        authorList.appendChild(item);
    });

    // Update filter count
    updateAuthorFilterCount();
}

// Set up author filter listeners
function setupAuthorFilters() {
    const searchInput = document.getElementById('authorSearchInput');
    const translationFilter = document.getElementById('authorTranslationFilter');

    // Only set up if not already done
    if (!searchInput.dataset.listenerAdded) {
        searchInput.addEventListener('input', filterAuthors);
        searchInput.dataset.listenerAdded = 'true';
    }

    if (!translationFilter.dataset.listenerAdded) {
        translationFilter.addEventListener('change', filterAuthors);
        translationFilter.dataset.listenerAdded = 'true';
    }
}

// Filter authors based on search and translation toggle
function filterAuthors() {
    const searchQuery = document.getElementById('authorSearchInput').value.toLowerCase();
    const onlyTranslated = document.getElementById('authorTranslationFilter').checked;

    filteredAuthors = allAuthors.filter(author => {
        // Search filter
        const matchesSearch = !searchQuery || author.name.toLowerCase().includes(searchQuery);

        // Translation filter
        const matchesTranslation = !onlyTranslated || author.has_translated_works;

        return matchesSearch && matchesTranslation;
    });

    displayAuthors();
}

// Update author filter count display
function updateAuthorFilterCount() {
    const countDiv = document.getElementById('authorFilterCount');

    if (filteredAuthors.length < allAuthors.length) {
        countDiv.textContent = `Showing ${filteredAuthors.length} of ${allAuthors.length} authors`;
        countDiv.style.display = 'block';
    } else {
        countDiv.style.display = 'none';
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

        // Store all works for filtering
        allWorks = works;
        filteredWorks = [...works];

        // Display works
        displayWorks();

        // Set up filter listeners
        setupWorkFilters();
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

    // Reset interlinear data cache when changing works
    interlinearData = null;
    
    // Check if this work has multiple books
    try {
        const response = await fetch(`/api/books/${workId}`);
        const books = await response.json();
        
        if (books.length === 1) {
            // Single book, load it directly
            await selectBook(books[0].id, workTitle, books[0].start_line, books[0].end_line);
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
async function selectBook(bookId, bookTitle, startLine, endLine, bookLabel = null) {
    currentBook = {
        id: bookId,
        title: bookTitle,
        label: bookLabel || bookTitle, // Store label for multi-book works
        startLine: startLine,
        endLine: endLine
    };
    currentPage = 1;

    // Reset interlinear data cache when changing books
    interlinearData = null;

    // Load available translators for this book
    await loadAvailableTranslators(bookId);
    
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
    } else if (viewMode === 'translation') {
        await loadTranslation(startLine, endLine);
    } else if (viewMode === 'interlinear') {
        await loadInterlinear(startLine, endLine);
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
        
        const language = getCurrentLanguage();
        const textClass = language === 'greek' ? 'greek-text' : 'latin-text';
        
        lines.forEach(line => {
            const lineDiv = document.createElement('div');
            lineDiv.className = 'text-line';
            
            const lineNumber = document.createElement('span');
            lineNumber.className = 'line-number';
            lineNumber.textContent = line.line_number;
            
            // Add speaker label if present
            if (line.speaker) {
                const speakerLabel = document.createElement('span');
                speakerLabel.className = 'speaker-label';
                speakerLabel.textContent = line.speaker;
                lineDiv.appendChild(speakerLabel);
            }
            
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
// Load available translators for a book
async function loadAvailableTranslators(bookId) {
    try {
        const response = await fetch(`/api/translators/${bookId}`);
        availableTranslators = await response.json();
        
        // Reset selected translator when switching books
        // Check if current translator exists for new book
        if (availableTranslators.length > 0) {
            if (!selectedTranslator || !availableTranslators.includes(selectedTranslator)) {
                // Select first available translator for this book
                selectedTranslator = availableTranslators[0];
            }
        } else {
            selectedTranslator = null;
        }
        
        // Update UI if there are multiple translators
        updateTranslatorSelector();
    } catch (error) {
        console.error('Error loading translators:', error);
        availableTranslators = [];
        selectedTranslator = null;
    }
}

// Update translator selector UI
function updateTranslatorSelector() {
    // Remove existing selector if any
    const existingSelector = document.getElementById('translatorSelector');
    if (existingSelector) {
        existingSelector.remove();
    }
    
    // Only show selector if there are multiple translators
    if (availableTranslators.length > 1) {
        const viewToggle = document.getElementById('viewToggle');
        const selector = document.createElement('div');
        selector.id = 'translatorSelector';
        selector.className = 'btn-group ms-2';
        selector.innerHTML = `
            <select class="form-select form-select-sm" onchange="selectTranslator(this.value)">
                ${availableTranslators.map(t => 
                    `<option value="${t}" ${t === selectedTranslator ? 'selected' : ''}>${t}</option>`
                ).join('')}
            </select>
        `;
        viewToggle.parentNode.insertBefore(selector, viewToggle.nextSibling);
    }
}

// Select a translator
window.selectTranslator = function(translator) {
    selectedTranslator = translator;
    if (viewMode === 'translation') {
        loadCurrentPage();
    }
}

async function loadTranslation(startLine, endLine) {
    try {
        showLoading('contentArea');
        // Include selected translator in the request
        const url = selectedTranslator 
            ? `/api/translation/${currentBook.id}/${startLine}/${endLine}?translator=${encodeURIComponent(selectedTranslator)}`
            : `/api/translation/${currentBook.id}/${startLine}/${endLine}`;
        const response = await fetch(url);
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

// Load interlinear translation
async function loadInterlinear(startLine, endLine) {
    try {
        // Load interlinear data if not already cached for this book
        if (!interlinearData) {
            showLoading('contentArea');
            const response = await fetch(`/api/interlinear/${currentBook.id}`);

            if (!response.ok) {
                throw new Error('No interlinear translation available');
            }

            interlinearData = await response.json();
        }

        // Get text lines for this page
        const textResponse = await fetch(`/api/text/${currentBook.id}/${startLine}/${endLine}`);
        const lines = await textResponse.json();

        const contentArea = document.getElementById('contentArea');
        contentArea.innerHTML = '';

        if (Object.keys(interlinearData).length === 0) {
            contentArea.innerHTML = '<p class="text-muted text-center mt-5">No interlinear translation available for this work.</p>';
            return;
        }

        const language = getCurrentLanguage();
        const textClass = language === 'greek' ? 'greek-text' : 'latin-text';

        lines.forEach(line => {
            const lineDiv = document.createElement('div');
            lineDiv.className = 'text-line';

            const lineNumber = document.createElement('span');
            lineNumber.className = 'line-number';
            lineNumber.textContent = line.line_number;
            lineDiv.appendChild(lineNumber);

            // Check if we have interlinear data for this line
            const interlinear = interlinearData[line.line_number];

            if (interlinear && interlinear.words) {
                // Create interlinear display
                const interlinearContainer = document.createElement('div');
                interlinearContainer.className = 'interlinear-container';

                // Display each word with its gloss and morphology
                for (let i = 0; i < interlinear.words.length; i++) {
                    const wordData = interlinear.words[i];
                    const wordTable = document.createElement('div');
                    wordTable.className = 'interlinear-word-table';

                    // Greek/Latin word (clickable)
                    const wordDiv = document.createElement('div');
                    wordDiv.className = `interlinear-word ${textClass} clickable-word`;
                    wordDiv.textContent = wordData.word;
                    wordDiv.onclick = () => lookupWord(wordData.word);

                    // English gloss
                    const glossDiv = document.createElement('div');
                    glossDiv.className = 'interlinear-gloss';
                    glossDiv.textContent = wordData.gloss;

                    // Morphology (if present)
                    if (wordData.morph && wordData.morph.trim()) {
                        const morphDiv = document.createElement('div');
                        morphDiv.className = 'interlinear-morph';
                        morphDiv.textContent = wordData.morph;

                        wordTable.appendChild(wordDiv);
                        wordTable.appendChild(glossDiv);
                        wordTable.appendChild(morphDiv);
                    } else {
                        wordTable.appendChild(wordDiv);
                        wordTable.appendChild(glossDiv);
                    }

                    interlinearContainer.appendChild(wordTable);
                }

                lineDiv.appendChild(interlinearContainer);
            } else {
                // No interlinear data, show regular text
                const lineText = document.createElement('span');
                lineText.className = textClass;
                lineText.innerHTML = makeWordsClickable(line.line_text, language);
                lineDiv.appendChild(lineText);
            }

            contentArea.appendChild(lineDiv);
        });

        // Disable next button if we got fewer lines than requested
        if (lines.length < linesPerPage) {
            document.getElementById('nextBtn').disabled = true;
        }
    } catch (error) {
        console.error('Error loading interlinear:', error);
        const contentArea = document.getElementById('contentArea');
        contentArea.innerHTML = '<p class="text-muted text-center mt-5">Interlinear translation not available for this work.</p>';
    }
}

// View mode switching
function showText() {
    viewMode = 'text';
    document.getElementById('textBtn').classList.add('active');
    document.getElementById('translationBtn').classList.remove('active');
    document.getElementById('interlinearBtn').classList.remove('active');
    if (currentBook) {
        loadPage();
    }
}

function showTranslation() {
    viewMode = 'translation';
    document.getElementById('translationBtn').classList.add('active');
    document.getElementById('textBtn').classList.remove('active');
    document.getElementById('interlinearBtn').classList.remove('active');
    if (currentBook) {
        loadPage();
    }
}

function showInterlinear() {
    viewMode = 'interlinear';
    document.getElementById('interlinearBtn').classList.add('active');
    document.getElementById('textBtn').classList.remove('active');
    document.getElementById('translationBtn').classList.remove('active');
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
    const language = getCurrentLanguage();
    
    // Show panel
    const panel = document.getElementById('wordInfoPanel');
    panel.classList.add('show');
    
    // Update selected word
    document.getElementById('selectedWord').textContent = word;
    
    // Store word for later occurrence fetch
    panel.dataset.currentWord = word;
    panel.dataset.currentLanguage = language;
    // Clear previous occurrences loaded flag
    delete panel.dataset.occurrencesLoaded;
    
    // Show loading state for dictionary only
    document.getElementById('dictionaryResults').innerHTML = '<div class="loading"><div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    
    // Clear occurrences and show placeholder
    document.getElementById('occurrencesResults').innerHTML = '<p class="text-muted">Click the Occurrences tab to search.</p>';
    
    // Make sure Dictionary tab is active
    document.getElementById('dictionary-tab').click();
    
    // Fetch dictionary entries immediately
    fetchDictionary(word, language);
}

// Fetch dictionary entries
async function fetchDictionary(word, language) {
    try {
        const response = await fetch(`/api/dictionary/${encodeURIComponent(word)}/${language}`);
        const data = await response.json();
        
        const resultsDiv = document.getElementById('dictionaryResults');
        
        // Handle both old format (array) and new format (object with entries)
        const entries = data.entries || (Array.isArray(data) ? data : []);
        const morphInfo = data.morph_info || null;
        
        // Display morph info next to the selected word
        const morphElement = document.getElementById('selectedWordMorph');
        if (morphElement && morphInfo && morphInfo.length > 0) {
            // Display the first morph_info entry
            morphElement.textContent = morphInfo[0].morph_info || '';
        } else if (morphElement) {
            morphElement.textContent = '';
        }
        
        if (entries.length === 0) {
            resultsDiv.innerHTML = '<p class="text-muted">No dictionary entries found.</p>';
            return;
        }
        
        resultsDiv.innerHTML = entries.map(entry => {
            // Get the text, preferring plain over HTML
            let text = entry.entry_plain || entry.entry_html || 'No definition available';
            
            // Strip ALL HTML tags
            if (text && text !== 'No definition available') {
                // Create a temporary element to strip HTML
                const temp = document.createElement('div');
                temp.innerHTML = text;
                text = temp.textContent || temp.innerText || text;
                
                // Clean up excessive whitespace
                text = text.replace(/\s+/g, ' ').trim();
            }
            
            // Format source name
            let sourceName = entry.source || 'Unknown';
            if (sourceName === 'lsj') sourceName = 'LSJ';
            else if (sourceName === 'cunliffe') sourceName = 'Cunliffe';
            else if (sourceName === 'wiktionary') sourceName = 'Wiktionary';
            else if (sourceName === 'lewis_short') sourceName = 'Lewis & Short';
            else if (sourceName === 'elementary_lewis') sourceName = 'Elementary Lewis';
            
            return `
                <div class="dictionary-entry">
                    <div class="dictionary-header">
                        <span class="dictionary-headword">${entry.headword}</span>
                        <span class="dictionary-source">${sourceName}</span>
                    </div>
                    <div class="dictionary-text">${text}</div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error fetching dictionary:', error);
        document.getElementById('dictionaryResults').innerHTML = '<p class="text-danger">Error loading dictionary entries.</p>';
    }
}

// Fetch word occurrences
async function fetchOccurrences(word, bookId) {
    try {
        const language = getCurrentLanguage();
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

// Greek text normalization - ported from Android app
function normalizeGreek(text) {
    // Remove punctuation (comma, period, semicolon, raised dot, colon, exclamation, question)
    let noPunctuation = text.replace(/[,;.·:!?]/g, '');
    
    // NFD normalization to separate base characters from diacritics
    // This separates the diacritics from the base characters
    let normalized = noPunctuation.normalize('NFD');
    
    // Remove combining marks (diacritics)
    // Unicode categories Mn (Non-spacing mark), Me (Enclosing mark), Mc (Spacing combining mark)
    let noCombining = '';
    for (let i = 0; i < normalized.length; i++) {
        const char = normalized[i];
        const code = char.charCodeAt(0);
        // Skip combining diacritical marks (0x0300-0x036F) and Greek extended combining marks
        if (!((code >= 0x0300 && code <= 0x036F) || (code >= 0x1AB0 && code <= 0x1AFF) || 
              (code >= 0x1DC0 && code <= 0x1DFF) || (code >= 0x20D0 && code <= 0x20FF) ||
              (code >= 0xFE20 && code <= 0xFE2F))) {
            noCombining += char;
        }
    }
    
    // Convert to lowercase
    let lowercased = noCombining.toLowerCase();
    
    // Replace final sigma with regular sigma
    let normalizedSigma = lowercased.replace(/ς/g, 'σ');
    
    // Keep only Greek letters
    let greekOnly = '';
    for (let i = 0; i < normalizedSigma.length; i++) {
        const char = normalizedSigma[i];
        const code = char.charCodeAt(0);
        // Greek and Coptic (0370-03FF) or Greek Extended (1F00-1FFF)
        if ((code >= 0x0370 && code <= 0x03FF) || (code >= 0x1F00 && code <= 0x1FFF)) {
            if (/\p{L}/u.test(char)) { // Is a letter
                greekOnly += char;
            }
        }
    }
    
    return greekOnly;
}

// Highlight word in occurrence text with better matching
function highlightWordInText(text, word, position) {
    const words = text.split(/\s+/);
    if (position > 0 && position <= words.length) {
        // Apply bold and background color like Android app
        const highlightStyle = 'background-color: #FFEB3B; color: #000; font-weight: bold; padding: 0 2px; border-radius: 2px;';
        words[position - 1] = `<span class="highlighted-word" style="${highlightStyle}">${words[position - 1]}</span>`;
    }
    return words.join(' ');
}

// Navigate to specific line
// Navigate to a specific book and line from search results
async function loadBookAndGoToLine(bookId, lineNumber) {
    try {
        // First, get book info to find the work and author
        const bookResponse = await fetch(`/api/books/${bookId}`);
        const bookData = await bookResponse.json();

        if (!bookData || bookData.length === 0) {
            console.error('Book not found');
            return;
        }

        const book = bookData[0];

        // Load the book
        await selectBook(book);

        // Calculate the page containing this line
        const page = Math.floor((lineNumber - book.start_line) / linesPerPage) + 1;
        currentPage = page;

        // Load the page containing the line
        await loadPage();

        // Highlight the specific line
        setTimeout(() => {
            const lines = document.querySelectorAll('.line-container');
            lines.forEach(line => {
                const lineNumElement = line.querySelector('.line-number');
                if (lineNumElement && parseInt(lineNumElement.textContent) === lineNumber) {
                    line.style.backgroundColor = '#ffeb3b';
                    line.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    setTimeout(() => {
                        line.style.backgroundColor = '';
                    }, 2000);
                }
            });
        }, 100);
    } catch (error) {
        console.error('Error navigating to book and line:', error);
    }
}

async function goToLine(bookId, lineNumber) {
    try {
        // Close the word panel
        closeWordPanel();
        
        // Parse the book ID to get author, work and book info
        const parts = bookId.split('.');
        const authorId = parts[0];
        const workId = parts.slice(0, 2).join('.');
        
        // Get author information
        const language = authorId.startsWith('tlg') ? 'greek' : 'latin';
        
        // Load and display authors if needed
        await loadAuthors();
        
        // Find and click the author
        const authorItem = document.querySelector(`[data-author-id="${authorId}"]`);
        if (!authorItem) {
            console.error('Author not found in list:', authorId);
            return;
        }
        
        // Click the author to load works
        authorItem.click();
        
        // Wait for works to load
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Find and click the work
        const workItem = document.querySelector(`[data-work-id="${workId}"]`);
        if (!workItem) {
            console.error('Work not found in list:', workId);
            return;
        }
        
        // Click the work
        workItem.click();
        
        // Wait for books to load
        await new Promise(resolve => setTimeout(resolve, 800));
        
        // Get book information
        const bookResponse = await fetch(`/api/books/${workId}`);
        const books = await bookResponse.json();
        const targetBook = books.find(b => b.id === bookId);
        
        if (!targetBook) {
            console.error('Book not found:', bookId);
            return;
        }
        
        // If multiple books, select the right one
        if (books.length > 1) {
            const bookItem = document.querySelector(`[data-book-id="${bookId}"]`);
            if (bookItem) {
                bookItem.click();
                await new Promise(resolve => setTimeout(resolve, 500));
            }
        } else {
            // Single book work - it should already be loading
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        
        // Calculate which page contains this line
        currentPage = Math.floor((lineNumber - 1) / linesPerPage) + 1;
        
        // Load the page containing the target line
        await loadPage();
        
        // Highlight the target line after a short delay to ensure content is loaded
        setTimeout(() => {
            const lines = document.querySelectorAll('.text-line');
            lines.forEach(line => {
                const lineNumElement = line.querySelector('.line-number');
                if (lineNumElement && parseInt(lineNumElement.textContent) === lineNumber) {
                    // Scroll to the line
                    const contentArea = document.getElementById('contentArea');
                    const cardBody = contentArea.closest('.card-body');
                    if (cardBody) {
                        // Calculate position within scrollable container
                        const lineTop = line.offsetTop;
                        const containerHeight = cardBody.clientHeight;
                        const scrollTo = lineTop - (containerHeight / 2) + (line.clientHeight / 2);
                        cardBody.scrollTop = Math.max(0, scrollTo);
                    }
                    
                    // Briefly highlight it
                    line.style.backgroundColor = '#ffeb3b';
                    setTimeout(() => {
                        line.style.backgroundColor = '';
                    }, 2000);
                }
            });
        }, 200);
        
    } catch (error) {
        console.error('Error navigating to line:', error);
    }
}

// Close word panel
function closeWordPanel() {
    const panel = document.getElementById('wordInfoPanel');
    panel.classList.remove('show');
    // Clear stored data
    delete panel.dataset.currentWord;
    delete panel.dataset.currentLanguage;
    delete panel.dataset.occurrencesLoaded;
}

// Load morphology when tab is clicked
function loadMorphologyIfNeeded() {
    const panel = document.getElementById('wordInfoPanel');
    const word = panel.dataset.currentWord;
    const language = panel.dataset.currentLanguage;

    // Only load if we haven't already loaded for this word
    if (word && !panel.dataset.morphologyLoaded) {
        // Show loading state
        document.getElementById('morphologyResults').innerHTML = '<div class="loading"><div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div></div>';

        // Fetch morphology
        fetchMorphology(word, language);

        // Mark as loaded
        panel.dataset.morphologyLoaded = 'true';
    }
}

// Fetch morphological analysis
async function fetchMorphology(word, language) {
    try {
        const response = await fetch(`/api/lemma/${encodeURIComponent(word)}/${language}`);
        const data = await response.json();

        const resultsDiv = document.getElementById('morphologyResults');

        if (!data.lemmas || data.lemmas.length === 0) {
            resultsDiv.innerHTML = '<p class="text-muted">No morphological analysis found.</p>';
            return;
        }

        resultsDiv.innerHTML = `
            <div class="morphology-container">
                ${data.lemmas.map(lemmaGroup => `
                    <div class="mb-3">
                        <h6 class="text-primary">Lemma: ${lemmaGroup.lemma}</h6>
                        <div class="small">
                            <strong>Forms found:</strong>
                            <div style="max-height: 200px; overflow-y: auto;">
                                ${lemmaGroup.forms.map(form => `
                                    <div class="d-flex justify-content-between align-items-start mb-1">
                                        <span class="font-monospace">${form.word_form}</span>
                                        ${form.morph_info ? `<span class="text-muted small ms-2">${form.morph_info}</span>` : ''}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (error) {
        console.error('Error fetching morphology:', error);
        document.getElementById('morphologyResults').innerHTML = '<p class="text-danger">Error loading morphological analysis.</p>';
    }
}

// Load occurrences when tab is clicked
function loadOccurrencesIfNeeded() {
    const panel = document.getElementById('wordInfoPanel');
    const word = panel.dataset.currentWord;
    const language = panel.dataset.currentLanguage;

    // Only load if we haven't already loaded for this word
    if (word && !panel.dataset.occurrencesLoaded) {
        // Show loading state
        document.getElementById('occurrencesResults').innerHTML = '<div class="loading"><div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div></div>';

        // Fetch occurrences
        fetchOccurrences(word, null);

        // Mark as loaded
        panel.dataset.occurrencesLoaded = 'true';
    }
}

// Search functionality
async function performSearch() {
    const searchTerm = document.getElementById('searchInput').value.trim();
    if (!searchTerm) return;

    const language = getCurrentLanguage();
    const lemmaSearch = document.getElementById('lemmaSearch').checked;

    try {
        const url = `/api/search/occurrences?word=${encodeURIComponent(searchTerm)}&language=${language}&lemma_search=${lemmaSearch}`;
        const response = await fetch(url);
        const data = await response.json();

        // Display results in the main content area
        const contentArea = document.getElementById('contentArea');

        if (data.length === 0) {
            contentArea.innerHTML = '<p class="text-muted text-center mt-5">No results found.</p>';
            return;
        }

        contentArea.innerHTML = `
            <h5>Search Results for "${searchTerm}"</h5>
            <p class="text-muted">Found ${data.length} occurrences${data.length >= 500 ? ' (showing first 500)' : ''}</p>
            <div style="max-height: 500px; overflow-y: auto;">
                ${data.map(result => `
                    <div class="search-result mb-2 p-2 border-bottom" style="cursor: pointer;"
                         onclick="loadBookAndGoToLine('${result.book_id}', ${result.line_number})">
                        <div class="small text-muted">
                            ${result.author_name} - ${result.work_title} - ${result.book_label} - Line ${result.line_number}
                        </div>
                        <div>${highlightWordInText(result.line_text, result.word, result.word_position)}</div>
                    </div>
                `).join('')}
            </div>
        `;

        // Update title
        document.getElementById('contentTitle').textContent = `Search Results`;
    } catch (error) {
        console.error('Error performing search:', error);
        document.getElementById('contentArea').innerHTML = '<p class="text-danger text-center mt-5">Error performing search.</p>';
    }
}

// Display filtered works
function displayWorks() {
    const bookList = document.getElementById('bookList');
    bookList.innerHTML = '';

    filteredWorks.forEach(work => {
        const item = document.createElement('a');
        item.href = '#';
        item.className = 'list-group-item list-group-item-action';
        const title = work.title_english || work.title;

        // Bold text for works with translations (like Android)
        if (work.has_translation) {
            item.innerHTML = `<strong>${title}</strong>`;
        } else {
            item.textContent = title;
        }

        item.dataset.workId = work.id; // Store ID for restoration
        item.onclick = (e) => {
            e.preventDefault();
            selectWork(work.id, title, item);
        };
        bookList.appendChild(item);
    });

    // Update filter count
    updateWorkFilterCount();
}

// Set up work filter listeners
function setupWorkFilters() {
    const searchInput = document.getElementById('workSearchInput');
    const translationFilter = document.getElementById('workTranslationFilter');

    // Only set up if not already done
    if (!searchInput.dataset.listenerAdded) {
        searchInput.addEventListener('input', filterWorks);
        searchInput.dataset.listenerAdded = 'true';
    }

    if (!translationFilter.dataset.listenerAdded) {
        translationFilter.addEventListener('change', filterWorks);
        translationFilter.dataset.listenerAdded = 'true';
    }
}

// Filter works based on search and translation toggle
function filterWorks() {
    const searchQuery = document.getElementById('workSearchInput').value.toLowerCase();
    const onlyTranslated = document.getElementById('workTranslationFilter').checked;

    filteredWorks = allWorks.filter(work => {
        const title = work.title_english || work.title;

        // Search filter
        const matchesSearch = !searchQuery || title.toLowerCase().includes(searchQuery);

        // Translation filter
        const matchesTranslation = !onlyTranslated || work.has_translation;

        return matchesSearch && matchesTranslation;
    });

    displayWorks();
}

// Update work filter count display
function updateWorkFilterCount() {
    const countDiv = document.getElementById('workFilterCount');

    if (filteredWorks.length < allWorks.length) {
        countDiv.textContent = `Showing ${filteredWorks.length} of ${allWorks.length} works`;
        countDiv.style.display = 'block';
    } else {
        countDiv.style.display = 'none';
    }
}

// Handle Enter key in search input
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }
});