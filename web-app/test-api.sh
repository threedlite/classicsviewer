#!/bin/bash

echo "Testing Classics Viewer Web API"
echo "==============================="

echo -e "\n1. Testing Greek authors endpoint:"
curl -s http://localhost:3000/api/authors/greek | python3 -m json.tool | head -5

echo -e "\n2. Testing Latin authors endpoint:"
curl -s http://localhost:3000/api/authors/latin | python3 -m json.tool | head -5

echo -e "\n3. Testing works for Achilles Tatius (tlg0532):"
curl -s http://localhost:3000/api/works/tlg0532 | python3 -m json.tool

echo -e "\n4. Testing books for a work:"
curl -s http://localhost:3000/api/books/tlg0532.tlg001 | python3 -m json.tool | head -10

echo -e "\n5. Testing text retrieval (first book, lines 1-5):"
BOOK_ID=$(curl -s http://localhost:3000/api/books/tlg0532.tlg001 | python3 -c "import json, sys; print(json.load(sys.stdin)[0]['id'])")
echo "Book ID: $BOOK_ID"
curl -s http://localhost:3000/api/text/$BOOK_ID/1/5 | python3 -m json.tool

echo -e "\n6. Testing translation retrieval:"
curl -s http://localhost:3000/api/translation/$BOOK_ID/1/5 | python3 -m json.tool | head -20

echo -e "\nAll tests completed!"