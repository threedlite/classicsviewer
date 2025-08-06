-- Translation Alignment Analysis Report
-- This query analyzes translation coverage and alignment for all Greek works

.headers on
.mode column

-- First, get summary statistics
SELECT 'Translation Summary Statistics' as analysis_section;
SELECT 
  COUNT(DISTINCT a.id) as authors_with_translations,
  COUNT(DISTINCT w.id) as works_with_translations,
  COUNT(DISTINCT ts.id) as total_translation_segments
FROM authors a 
JOIN works w ON a.id = w.author_id 
JOIN translation_segments ts ON w.id = ts.book_id
WHERE a.language = 'greek';

-- Now analyze alignment issues
SELECT '';
SELECT 'Works with Translation Alignment Issues' as analysis_section;
SELECT 
  a.name as author,
  w.title_english as work,
  (SELECT COUNT(*) FROM text_lines tl WHERE tl.book_id = w.id) as total_lines,
  (SELECT COUNT(DISTINCT ts.id) FROM translation_segments ts WHERE ts.book_id = w.id) as translation_segments,
  (SELECT MIN(ts.start_line) FROM translation_segments ts WHERE ts.book_id = w.id) as min_trans_line,
  (SELECT MAX(COALESCE(ts.end_line, ts.start_line)) FROM translation_segments ts WHERE ts.book_id = w.id) as max_trans_line,
  ROUND((SELECT MAX(COALESCE(ts.end_line, ts.start_line)) FROM translation_segments ts WHERE ts.book_id = w.id) * 100.0 / 
        (SELECT COUNT(*) FROM text_lines tl WHERE tl.book_id = w.id), 1) as coverage_percent,
  CASE 
    WHEN (SELECT MAX(COALESCE(ts.end_line, ts.start_line)) FROM translation_segments ts WHERE ts.book_id = w.id) < 
         (SELECT COUNT(*) FROM text_lines tl WHERE tl.book_id = w.id) * 0.5
    THEN 'SEVERELY_MISALIGNED'
    WHEN (SELECT MAX(COALESCE(ts.end_line, ts.start_line)) FROM translation_segments ts WHERE ts.book_id = w.id) < 
         (SELECT COUNT(*) FROM text_lines tl WHERE tl.book_id = w.id) * 0.8 
    THEN 'MISALIGNED'
    ELSE 'ALIGNED'
  END as alignment_status
FROM authors a 
JOIN works w ON a.id = w.author_id 
WHERE w.id IN (SELECT DISTINCT book_id FROM translation_segments)
AND a.language = 'greek'
ORDER BY 
  CASE WHEN a.name LIKE '%Aristotle%' THEN 0 ELSE 1 END,
  coverage_percent ASC;