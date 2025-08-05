#!/usr/bin/env python3
"""
Add mappings for adverbs, superlatives, and other derived forms
"""

import sqlite3
import unicodedata

def normalize_greek(text):
    """Normalize Greek text"""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = text.replace('ς', 'σ')
    text = ''.join(c for c in text if c.isalpha() and ('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff'))
    return text

def add_morphological_mappings():
    conn = sqlite3.connect('perseus_texts.db')
    cursor = conn.cursor()
    
    mappings = []
    
    # 1. Common adverbs from adjectives
    adverb_mappings = [
        ('κακωσ', 'κακοσ', 'adverb'),  # badly from κακός
        ('ορθωσ', 'ορθοσ', 'adverb'),  # correctly from ὀρθός
        ('καλωσ', 'καλοσ', 'adverb'),  # well from καλός
        ('ευ', 'ευσ', 'adverb'),       # well
        ('σαφωσ', 'σαφησ', 'adverb'),  # clearly from σαφής
        ('αληθωσ', 'αληθησ', 'adverb'), # truly from ἀληθής
        ('ομοιωσ', 'ομοιοσ', 'adverb'), # similarly from ὅμοιος
        ('ηττον', 'ησσων', 'adverb_comparative'), # less from ἥσσων
        ('μαλλον', 'μαλα', 'adverb_comparative'), # more from μάλα
    ]
    
    # 2. Superlatives and comparatives
    superlative_mappings = [
        ('μαλιστα', 'μαλα', 'adverb_superlative'),  # most from μάλα
        ('πρωτον', 'πρωτοσ', 'neuter_acc_sg'),      # first (neuter)
        ('πρωτοσ', 'πρωτοσ', 'lemma'),              # first (masculine)
        ('μεγιστον', 'μεγασ', 'superlative_neut_acc_sg'), # greatest
    ]
    
    # 3. Pronoun forms
    pronoun_mappings = [
        ('ημιν', 'εγω', '1p_dat_pl'),    # to us
        ('ημασ', 'εγω', '1p_acc_pl'),    # us
        ('ημεισ', 'εγω', '1p_nom_pl'),   # we
        ('υμιν', 'συ', '2p_dat_pl'),     # to you (pl)
        ('υμασ', 'συ', '2p_acc_pl'),     # you (pl)
        ('υμεισ', 'συ', '2p_nom_pl'),    # you (pl)
        ('υμων', 'συ', '2p_gen_pl'),     # of you (pl)
        ('εμοι', 'εγω', '1s_dat'),       # to me
        ('εμε', 'εγω', '1s_acc'),        # me
        ('μου', 'εγω', '1s_gen'),        # of me
        ('μοι', 'εγω', '1s_dat'),        # to me
        ('σου', 'συ', '2s_gen'),         # of you
        ('σοι', 'συ', '2s_dat'),         # to you
        ('σε', 'συ', '2s_acc'),          # you
    ]
    
    # 4. Negatives and particles
    particle_mappings = [
        ('ουχ', 'ου', 'negative_rough'),  # not (before rough breathing)
        ('ουχι', 'ου', 'negative_emphatic'), # not at all
        ('μη', 'μη', 'negative_subjunctive'), # not (subjunctive/imperative)
        ('μητ', 'μη', 'negative_elided'),    # not (elided)
        ('ουκ', 'ου', 'negative_smooth'),    # not (before smooth breathing)
        ('ουδ', 'ουδε', 'conjunction_elided'), # and not (elided)
    ]
    
    # 5. Elided prepositions
    preposition_mappings = [
        ('υπ', 'υπο', 'preposition_elided'),
        ('απ', 'απο', 'preposition_elided'),
        ('εφ', 'επι', 'preposition_elided_rough'),
        ('επ', 'επι', 'preposition_elided'),
        ('εξ', 'εκ', 'preposition_prevocalic'),
        ('εισ', 'εισ', 'preposition_acc'),
        ('εκ', 'εκ', 'preposition_gen'),
        ('προσ', 'προσ', 'preposition_acc'),
    ]
    
    # 6. Common particles and conjunctions
    particle_conj_mappings = [
        ('αυταρ', 'αυταρ', 'particle'),      # but, moreover (epic)
        ('μεντοι', 'μεντοι', 'particle'),    # however
        ('εγωγε', 'εγω', 'pronoun_emphatic'), # I at least
        ('καθαπερ', 'καθαπερ', 'conjunction'), # just as
        ('επειδη', 'επειδη', 'conjunction'),   # when, since
        ('ωστ', 'ωστε', 'conjunction_elided'), # so that (elided)
        ('τοδ', 'οδε', 'demonstrative_neut_acc'), # this (neuter)
        ('ταδ', 'οδε', 'demonstrative_neut_acc_pl'), # these (neuter)
        ('τουτ', 'ουτοσ', 'demonstrative_neut_nom_acc'), # this (elided)
        ('ταλλα', 'αλλοσ', 'pronoun_neut_acc_pl_crasis'), # the other things (τὰ ἄλλα)
    ]
    
    # 7. Common verbs and participles
    verb_mappings = [
        ('εχοντα', 'εχω', 'participle_pres_act_masc_acc_sg'),
        ('εχοντεσ', 'εχω', 'participle_pres_act_masc_nom_pl'),
        ('πραττειν', 'πρασσω', 'infinitive_pres_act'),
        ('χαιρειν', 'χαιρω', 'infinitive_pres_act'),
        ('φρονειν', 'φρονεω', 'infinitive_pres_act'),
        ('γενομενησ', 'γιγνομαι', 'participle_aor_mid_fem_gen_sg'),
    ]
    
    # Combine all mappings
    all_mappings = (adverb_mappings + superlative_mappings + pronoun_mappings + 
                    particle_mappings + preposition_mappings + particle_conj_mappings + 
                    verb_mappings)
    
    # Insert mappings
    count = 0
    for word_form, lemma, morph_info in all_mappings:
        # Check if mapping already exists
        cursor.execute("""
            SELECT 1 FROM lemma_map 
            WHERE word_normalized = ? AND lemma = ?
        """, (word_form, lemma))
        
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO lemma_map (word_form, word_normalized, lemma, morph_info, source, confidence)
                VALUES (?, ?, ?, ?, 'manual_common_forms', 1.0)
            """, (word_form, word_form, lemma, morph_info))
            count += 1
    
    # Add Roman names (proper nouns)
    roman_names = [
        ('ρωμαιων', 'ρωμαιοσ', 'proper_noun_gen_pl'),
        ('καισαροσ', 'καισαρ', 'proper_noun_gen_sg'),
        ('καισαρ', 'καισαρ', 'proper_noun_nom'),
        ('πομπηιον', 'πομπηιοσ', 'proper_noun_acc_sg'),
        ('πομπηιοσ', 'πομπηιοσ', 'proper_noun_nom'),
        ('πομπηιου', 'πομπηιοσ', 'proper_noun_gen_sg'),
    ]
    
    for word_form, lemma, morph_info in roman_names:
        cursor.execute("""
            SELECT 1 FROM lemma_map 
            WHERE word_normalized = ? AND lemma = ?
        """, (word_form, lemma))
        
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO lemma_map (word_form, word_normalized, lemma, morph_info, source, confidence)
                VALUES (?, ?, ?, ?, 'proper_nouns', 0.9)
            """, (word_form, word_form, lemma, morph_info))
            count += 1
    
    conn.commit()
    print(f"Added {count} new morphological mappings")
    
    # Now check if these lemmas exist in dictionary
    print("\nChecking which lemmas need dictionary entries:")
    missing_lemmas = []
    
    for _, lemma, _ in all_mappings + roman_names:
        cursor.execute("""
            SELECT 1 FROM dictionary_entries 
            WHERE headword_normalized = ? AND language = 'greek'
        """, (lemma,))
        
        if not cursor.fetchone() and lemma not in missing_lemmas:
            missing_lemmas.append(lemma)
    
    if missing_lemmas:
        print(f"Lemmas missing from dictionary: {missing_lemmas}")
    else:
        print("All lemmas have dictionary entries!")
    
    conn.close()

if __name__ == '__main__':
    add_morphological_mappings()