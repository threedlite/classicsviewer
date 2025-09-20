
Tags we EXCLUDE (these contain metadata/commentary, not main text):
  - note - Editorial notes and commentary
  - foreign - Foreign language glosses/translations
  - ref - Cross-references
  - bibl - Bibliographic references
  - del - Deleted text (not the main reading)
  - gap - Lacunae where text is missing
  - rdg - Alternative readings (not the main text)

  Tags we KEEP (these contain actual text content):
  - add - Editorial additions that complete the text
  - corr - Corrections that should be shown
  - supplied - Text reconstructed by scholars
  - unclear - Text that's unclear but still readable
  - sic - Original text preserved as-is
  - lem - The main reading in critical apparatus
  - choice - Contains alternatives but needs processing
  - app - Critical apparatus container

 1911                                # Process each sentence as a line
       1912                                for sentence in sentences:
       1913                                    sentence = sentence.strip()
       1914 -                                  # Filter out editorial notes
       1915 -                                  if (sentence and len(sentence) > 10 and 
       1916 -                                      not re.match(r'^[A-Z]:', sentence) and
       1917 -                                      not sentence.startswith('em.') and
       1918 -                                      not sentence.startswith('add.') and
       1919 -                                      'Nauck' not in sentence and
       1920 -                                      'Mullach' not in sentence and
       1921 -                                      not sentence.startswith('id.')):
       1914 +                                  # Filter out very short sentences
       1915 +                                  if sentence and len(sentence) > 10:
       1916                                        line_num += 1
       1917                                        all_lines.append({
       1918                                            'number': line_num,
     ...
       2052                            # Process each sentence as a line
       2053                            for sentence in sentences:
       2054                                sentence = sentence.strip()
       2055 -                              # Filter out editorial notes and very short sentences
       2056 -                              if (sentence and len(sentence) > 10 and 
       2057 -                                  not re.match(r'^[A-Z]:', sentence) and  # Skip "W:" style notes
       2058 -                                  not sentence.startswith('em.') and      # Skip "em." notes
       2059 -                                  not sentence.startswith('add.') and     # Skip "add." notes
       2060 -                                  'Nauck' not in sentence and             # Skip Nauck references
       2061 -                                  'Mullach' not in sentence and           # Skip Mullach references
       2062 -                                  not sentence.startswith('id.')):        # Skip "id." references
       2055 +                              # Filter out very short sentences
       2056 +                              if sentence and len(sentence) > 10:
       2057                                    line_num += 1
       2058                                    # Add milestone reference for Plato/Aristotle
       2059                                    if (is_plato or is_aristotle) and current_milestone:
     ...
       2109                        
       2110                        for sentence in sentences:
       2111                            sentence = sentence.strip()
       2112 -                          # Filter out editorial notes and very short sentences
       2113 -                          if (sentence and len(sentence) > 20 and 
       2114 -                              not re.match(r'^[A-Z]:', sentence) and  # Skip "W:" style notes
       2115 -                              not sentence.startswith('em.') and      # Skip "em." notes
       2116 -                              not sentence.startswith('add.') and     # Skip "add." notes
       2117 -                              'Nauck' not in sentence and             # Skip Nauck references
       2118 -                              'Mullach' not in sentence):             # Skip Mullach references
       2112 +                          # Filter out very short sentences
       2113 +                          if sentence and len(sentence) > 20:
       2114                                line_num += 1
       2115                                # Add milestone reference for Plato/Aristotle
       2116                                if (is_plato or is_aristotle) and current_milestone:



