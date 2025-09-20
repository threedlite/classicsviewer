#!/usr/bin/env python3
"""
Create an Entity-Relationship diagram for the perseus_texts.db database
"""

import graphviz

def create_er_diagram():
    # Create a new directed graph
    dot = graphviz.Digraph(comment='Perseus Texts Database Schema', engine='dot')
    dot.attr(rankdir='TB', splines='ortho', nodesep='0.5', ranksep='1.0')
    
    # Define colors
    primary_color = '#4a90e2'
    foreign_color = '#7cb342'
    index_color = '#ffa726'
    table_bg = '#f5f5f5'
    
    # Define node style for tables
    dot.attr('node', shape='none', margin='0')
    
    # Create table nodes with HTML-like labels
    
    # Authors table
    authors_label = '''<
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4" BGCOLOR="{bg}">
        <TR><TD COLSPAN="2" BGCOLOR="{primary}" ALIGN="CENTER"><FONT COLOR="white"><B>authors</B></FONT></TD></TR>
        <TR><TD ALIGN="LEFT" PORT="id"><B>id</B></TD><TD ALIGN="LEFT">TEXT PK</TD></TR>
        <TR><TD ALIGN="LEFT">name</TD><TD ALIGN="LEFT">TEXT NOT NULL</TD></TR>
        <TR><TD ALIGN="LEFT">name_alt</TD><TD ALIGN="LEFT">TEXT</TD></TR>
        <TR><TD ALIGN="LEFT">language</TD><TD ALIGN="LEFT">TEXT NOT NULL</TD></TR>
        <TR><TD ALIGN="LEFT">has_translations</TD><TD ALIGN="LEFT">INTEGER DEFAULT 0</TD></TR>
        <TR><TD COLSPAN="2" BGCOLOR="{index}" ALIGN="CENTER"><FONT COLOR="white">INDEX: language</FONT></TD></TR>
    </TABLE>>'''.format(bg=table_bg, primary=primary_color, index=index_color)
    dot.node('authors', authors_label)
    
    # Works table
    works_label = '''<
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4" BGCOLOR="{bg}">
        <TR><TD COLSPAN="2" BGCOLOR="{primary}" ALIGN="CENTER"><FONT COLOR="white"><B>works</B></FONT></TD></TR>
        <TR><TD ALIGN="LEFT" PORT="id"><B>id</B></TD><TD ALIGN="LEFT">TEXT PK</TD></TR>
        <TR><TD ALIGN="LEFT" PORT="author_id"><FONT COLOR="{foreign}">author_id</FONT></TD><TD ALIGN="LEFT">TEXT NOT NULL FK</TD></TR>
        <TR><TD ALIGN="LEFT">title</TD><TD ALIGN="LEFT">TEXT NOT NULL</TD></TR>
        <TR><TD ALIGN="LEFT">title_alt</TD><TD ALIGN="LEFT">TEXT</TD></TR>
        <TR><TD ALIGN="LEFT">title_english</TD><TD ALIGN="LEFT">TEXT</TD></TR>
        <TR><TD ALIGN="LEFT">type</TD><TD ALIGN="LEFT">TEXT</TD></TR>
        <TR><TD ALIGN="LEFT">urn</TD><TD ALIGN="LEFT">TEXT</TD></TR>
        <TR><TD ALIGN="LEFT">description</TD><TD ALIGN="LEFT">TEXT</TD></TR>
        <TR><TD COLSPAN="2" BGCOLOR="{index}" ALIGN="CENTER"><FONT COLOR="white">INDEX: author_id</FONT></TD></TR>
    </TABLE>>'''.format(bg=table_bg, primary=primary_color, foreign=foreign_color, index=index_color)
    dot.node('works', works_label)
    
    # Books table
    books_label = '''<
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4" BGCOLOR="{bg}">
        <TR><TD COLSPAN="2" BGCOLOR="{primary}" ALIGN="CENTER"><FONT COLOR="white"><B>books</B></FONT></TD></TR>
        <TR><TD ALIGN="LEFT" PORT="id"><B>id</B></TD><TD ALIGN="LEFT">TEXT PK</TD></TR>
        <TR><TD ALIGN="LEFT" PORT="work_id"><FONT COLOR="{foreign}">work_id</FONT></TD><TD ALIGN="LEFT">TEXT NOT NULL FK</TD></TR>
        <TR><TD ALIGN="LEFT">book_number</TD><TD ALIGN="LEFT">INTEGER NOT NULL</TD></TR>
        <TR><TD ALIGN="LEFT">label</TD><TD ALIGN="LEFT">TEXT</TD></TR>
        <TR><TD ALIGN="LEFT">start_line</TD><TD ALIGN="LEFT">INTEGER</TD></TR>
        <TR><TD ALIGN="LEFT">end_line</TD><TD ALIGN="LEFT">INTEGER</TD></TR>
        <TR><TD ALIGN="LEFT">line_count</TD><TD ALIGN="LEFT">INTEGER</TD></TR>
        <TR><TD COLSPAN="2" BGCOLOR="{index}" ALIGN="CENTER"><FONT COLOR="white">INDEX: work_id</FONT></TD></TR>
    </TABLE>>'''.format(bg=table_bg, primary=primary_color, foreign=foreign_color, index=index_color)
    dot.node('books', books_label)
    
    # Text lines table
    text_lines_label = '''<
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4" BGCOLOR="{bg}">
        <TR><TD COLSPAN="2" BGCOLOR="{primary}" ALIGN="CENTER"><FONT COLOR="white"><B>text_lines</B></FONT></TD></TR>
        <TR><TD ALIGN="LEFT" PORT="id"><B>id</B></TD><TD ALIGN="LEFT">INTEGER PK AUTOINCREMENT</TD></TR>
        <TR><TD ALIGN="LEFT" PORT="book_id"><FONT COLOR="{foreign}">book_id</FONT></TD><TD ALIGN="LEFT">TEXT NOT NULL FK</TD></TR>
        <TR><TD ALIGN="LEFT">line_number</TD><TD ALIGN="LEFT">INTEGER NOT NULL</TD></TR>
        <TR><TD ALIGN="LEFT">line_text</TD><TD ALIGN="LEFT">TEXT NOT NULL</TD></TR>
        <TR><TD ALIGN="LEFT">line_xml</TD><TD ALIGN="LEFT">TEXT</TD></TR>
        <TR><TD ALIGN="LEFT">speaker</TD><TD ALIGN="LEFT">TEXT</TD></TR>
        <TR><TD COLSPAN="2" BGCOLOR="{index}" ALIGN="CENTER"><FONT COLOR="white">INDEX: book_id</FONT></TD></TR>
    </TABLE>>'''.format(bg=table_bg, primary=primary_color, foreign=foreign_color, index=index_color)
    dot.node('text_lines', text_lines_label)
    
    # Translation segments table
    translation_segments_label = '''<
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4" BGCOLOR="{bg}">
        <TR><TD COLSPAN="2" BGCOLOR="{primary}" ALIGN="CENTER"><FONT COLOR="white"><B>translation_segments</B></FONT></TD></TR>
        <TR><TD ALIGN="LEFT" PORT="id"><B>id</B></TD><TD ALIGN="LEFT">INTEGER PK AUTOINCREMENT</TD></TR>
        <TR><TD ALIGN="LEFT" PORT="book_id"><FONT COLOR="{foreign}">book_id</FONT></TD><TD ALIGN="LEFT">TEXT NOT NULL FK</TD></TR>
        <TR><TD ALIGN="LEFT">start_line</TD><TD ALIGN="LEFT">INTEGER NOT NULL</TD></TR>
        <TR><TD ALIGN="LEFT">end_line</TD><TD ALIGN="LEFT">INTEGER</TD></TR>
        <TR><TD ALIGN="LEFT">translation_text</TD><TD ALIGN="LEFT">TEXT NOT NULL</TD></TR>
        <TR><TD ALIGN="LEFT">translator</TD><TD ALIGN="LEFT">TEXT</TD></TR>
        <TR><TD ALIGN="LEFT">speaker</TD><TD ALIGN="LEFT">TEXT</TD></TR>
        <TR><TD COLSPAN="2" BGCOLOR="{index}" ALIGN="CENTER"><FONT COLOR="white">INDEX: book_id, start_line</FONT></TD></TR>
    </TABLE>>'''.format(bg=table_bg, primary=primary_color, foreign=foreign_color, index=index_color)
    dot.node('translation_segments', translation_segments_label)
    
    # Words table
    words_label = '''<
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4" BGCOLOR="{bg}">
        <TR><TD COLSPAN="2" BGCOLOR="{primary}" ALIGN="CENTER"><FONT COLOR="white"><B>words</B></FONT></TD></TR>
        <TR><TD ALIGN="LEFT" PORT="id"><B>id</B></TD><TD ALIGN="LEFT">INTEGER PK AUTOINCREMENT</TD></TR>
        <TR><TD ALIGN="LEFT">word</TD><TD ALIGN="LEFT">TEXT NOT NULL</TD></TR>
        <TR><TD ALIGN="LEFT">word_normalized</TD><TD ALIGN="LEFT">TEXT NOT NULL</TD></TR>
        <TR><TD ALIGN="LEFT" PORT="book_id"><FONT COLOR="{foreign}">book_id</FONT></TD><TD ALIGN="LEFT">TEXT NOT NULL FK</TD></TR>
        <TR><TD ALIGN="LEFT">line_number</TD><TD ALIGN="LEFT">INTEGER NOT NULL</TD></TR>
        <TR><TD ALIGN="LEFT">word_position</TD><TD ALIGN="LEFT">INTEGER NOT NULL</TD></TR>
        <TR><TD COLSPAN="2" BGCOLOR="{index}" ALIGN="CENTER"><FONT COLOR="white">INDEX: word_normalized</FONT></TD></TR>
        <TR><TD COLSPAN="2" BGCOLOR="{index}" ALIGN="CENTER"><FONT COLOR="white">INDEX: book_id, line_number</FONT></TD></TR>
    </TABLE>>'''.format(bg=table_bg, primary=primary_color, foreign=foreign_color, index=index_color)
    dot.node('words', words_label)
    
    # Dictionary entries table
    dictionary_entries_label = '''<
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4" BGCOLOR="{bg}">
        <TR><TD COLSPAN="2" BGCOLOR="{primary}" ALIGN="CENTER"><FONT COLOR="white"><B>dictionary_entries</B></FONT></TD></TR>
        <TR><TD ALIGN="LEFT" PORT="id"><B>id</B></TD><TD ALIGN="LEFT">INTEGER PK</TD></TR>
        <TR><TD ALIGN="LEFT">headword</TD><TD ALIGN="LEFT">TEXT NOT NULL</TD></TR>
        <TR><TD ALIGN="LEFT">headword_normalized</TD><TD ALIGN="LEFT">TEXT NOT NULL</TD></TR>
        <TR><TD ALIGN="LEFT">language</TD><TD ALIGN="LEFT">TEXT NOT NULL (greek/latin)</TD></TR>
        <TR><TD ALIGN="LEFT">entry_xml</TD><TD ALIGN="LEFT">TEXT</TD></TR>
        <TR><TD ALIGN="LEFT">entry_html</TD><TD ALIGN="LEFT">TEXT</TD></TR>
        <TR><TD ALIGN="LEFT">entry_plain</TD><TD ALIGN="LEFT">TEXT</TD></TR>
        <TR><TD ALIGN="LEFT">source</TD><TD ALIGN="LEFT">TEXT</TD></TR>
        <TR><TD COLSPAN="2" BGCOLOR="{index}" ALIGN="CENTER"><FONT COLOR="white">INDEX: headword_normalized, language</FONT></TD></TR>
    </TABLE>>'''.format(bg=table_bg, primary=primary_color, index=index_color)
    dot.node('dictionary_entries', dictionary_entries_label)
    
    # Lemma map table
    lemma_map_label = '''<
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4" BGCOLOR="{bg}">
        <TR><TD COLSPAN="2" BGCOLOR="{primary}" ALIGN="CENTER"><FONT COLOR="white"><B>lemma_map</B></FONT></TD></TR>
        <TR><TD ALIGN="LEFT"><B>word_form</B></TD><TD ALIGN="LEFT">TEXT NOT NULL (PK)</TD></TR>
        <TR><TD ALIGN="LEFT">word_normalized</TD><TD ALIGN="LEFT">TEXT NOT NULL</TD></TR>
        <TR><TD ALIGN="LEFT"><B>lemma</B></TD><TD ALIGN="LEFT">TEXT NOT NULL (PK)</TD></TR>
        <TR><TD ALIGN="LEFT">confidence</TD><TD ALIGN="LEFT">REAL DEFAULT 1.0</TD></TR>
        <TR><TD ALIGN="LEFT">source</TD><TD ALIGN="LEFT">TEXT</TD></TR>
        <TR><TD ALIGN="LEFT">morph_info</TD><TD ALIGN="LEFT">TEXT</TD></TR>
        <TR><TD COLSPAN="2" BGCOLOR="{index}" ALIGN="CENTER"><FONT COLOR="white">INDEX: word_form</FONT></TD></TR>
        <TR><TD COLSPAN="2" BGCOLOR="{index}" ALIGN="CENTER"><FONT COLOR="white">INDEX: lemma</FONT></TD></TR>
    </TABLE>>'''.format(bg=table_bg, primary=primary_color, index=index_color)
    dot.node('lemma_map', lemma_map_label)
    
    # Translation lookup table
    translation_lookup_label = '''<
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4" BGCOLOR="{bg}">
        <TR><TD COLSPAN="2" BGCOLOR="{primary}" ALIGN="CENTER"><FONT COLOR="white"><B>translation_lookup</B></FONT></TD></TR>
        <TR><TD ALIGN="LEFT" PORT="book_id"><B><FONT COLOR="{foreign}">book_id</FONT></B></TD><TD ALIGN="LEFT">TEXT NOT NULL (PK, FK)</TD></TR>
        <TR><TD ALIGN="LEFT"><B>line_number</B></TD><TD ALIGN="LEFT">INTEGER NOT NULL (PK)</TD></TR>
        <TR><TD ALIGN="LEFT" PORT="segment_id"><B><FONT COLOR="{foreign}">segment_id</FONT></B></TD><TD ALIGN="LEFT">INTEGER NOT NULL (PK, FK)</TD></TR>
        <TR><TD COLSPAN="2" BGCOLOR="{index}" ALIGN="CENTER"><FONT COLOR="white">INDEX: book_id, line_number</FONT></TD></TR>
        <TR><TD COLSPAN="2" BGCOLOR="{index}" ALIGN="CENTER"><FONT COLOR="white">INDEX: segment_id</FONT></TD></TR>
    </TABLE>>'''.format(bg=table_bg, primary=primary_color, foreign=foreign_color, index=index_color)
    dot.node('translation_lookup', translation_lookup_label)
    
    # Add relationships (edges)
    dot.edge('works:author_id', 'authors:id', color=foreign_color, penwidth='2')
    dot.edge('books:work_id', 'works:id', color=foreign_color, penwidth='2')
    dot.edge('text_lines:book_id', 'books:id', color=foreign_color, penwidth='2')
    dot.edge('translation_segments:book_id', 'books:id', color=foreign_color, penwidth='2')
    dot.edge('words:book_id', 'books:id', color=foreign_color, penwidth='2')
    dot.edge('translation_lookup:book_id', 'books:id', color=foreign_color, penwidth='2')
    dot.edge('translation_lookup:segment_id', 'translation_segments:id', color=foreign_color, penwidth='2')
    
    # Render the diagram
    dot.render('perseus_texts_er_diagram', format='pdf', cleanup=True)
    print("ER diagram saved as perseus_texts_er_diagram.pdf")

if __name__ == '__main__':
    create_er_diagram()