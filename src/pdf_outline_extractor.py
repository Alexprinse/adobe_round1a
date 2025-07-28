#!/usr/bin/env python3
"""
PDF Outline Extractor for Hackathon Round 1A
Extracts structured outline (title, H1, H2, H3 headings) from PDF files.
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse

try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF not found. Please install with: pip install PyMuPDF")
    exit(1)

try:
    import pdfplumber
except ImportError:
    print("pdfplumber not found. Please install with: pip install pdfplumber")
    exit(1)


class PDFOutlineExtractor:
    """Extract structured outline from PDF documents with multilingual support."""
    
    def __init__(self):
        self.setup_logging()
        self.detected_lists = []  # Track all detected lists for summary
        self.setup_multilingual_patterns()
        
    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def setup_multilingual_patterns(self):
        """Setup multilingual patterns for different languages."""
        
        # Heading keywords in different languages
        self.heading_keywords = {
            'en': {
                'part': ['part', 'section'],
                'appendix': ['appendix', 'annex'],
                'chapter': ['chapter', 'chap'],
                'introduction': ['introduction', 'intro'],
                'conclusion': ['conclusion', 'summary'],
                'references': ['references', 'bibliography', 'citations'],
                'table_of_contents': ['table of contents', 'contents', 'toc']
            },
            'ja': {  # Japanese
                'part': ['部', '章', 'パート', '第.*部', '第.*章'],
                'appendix': ['付録', '別添', '添付', '参考資料'],
                'chapter': ['章', '第.*章', 'チャプター'],
                'introduction': ['はじめに', '序論', '導入', '概要', 'まえがき'],
                'conclusion': ['結論', 'まとめ', 'おわりに', '総括'],
                'references': ['参考文献', '引用文献', '文献', '参照'],
                'table_of_contents': ['目次', '内容', 'もくじ']
            },
            'zh': {  # Chinese (Simplified & Traditional)
                'part': ['部分', '部', '章', '第.*部', '第.*章'],
                'appendix': ['附录', '附錄', '附件', '参考资料', '參考資料'],
                'chapter': ['章', '第.*章', '章节', '章節'],
                'introduction': ['介绍', '介紹', '序言', '导言', '導言', '概述'],
                'conclusion': ['结论', '結論', '总结', '總結', '小结', '小結'],
                'references': ['参考文献', '參考文獻', '引用文献', '引用文獻', '文献', '文獻'],
                'table_of_contents': ['目录', '目錄', '内容', '內容']
            },
            'es': {  # Spanish
                'part': ['parte', 'sección', 'capítulo'],
                'appendix': ['apéndice', 'anexo', 'adjunto'],
                'chapter': ['capítulo', 'cap'],
                'introduction': ['introducción', 'intro', 'presentación'],
                'conclusion': ['conclusión', 'resumen', 'síntesis'],
                'references': ['referencias', 'bibliografía', 'citas'],
                'table_of_contents': ['índice', 'contenido', 'tabla de contenidos']
            },
            'fr': {  # French
                'part': ['partie', 'section', 'chapitre'],
                'appendix': ['annexe', 'appendice', 'complément'],
                'chapter': ['chapitre', 'chap'],
                'introduction': ['introduction', 'présentation', 'avant-propos'],
                'conclusion': ['conclusion', 'résumé', 'synthèse'],
                'references': ['références', 'bibliographie', 'citations'],
                'table_of_contents': ['table des matières', 'sommaire', 'contenu']
            },
            'de': {  # German
                'part': ['teil', 'abschnitt', 'kapitel'],
                'appendix': ['anhang', 'anlage', 'beilage'],
                'chapter': ['kapitel', 'kap'],
                'introduction': ['einführung', 'einleitung', 'vorwort'],
                'conclusion': ['schlussfolgerung', 'zusammenfassung', 'fazit'],
                'references': ['literatur', 'bibliographie', 'quellen'],
                'table_of_contents': ['inhaltsverzeichnis', 'inhalt']
            },
            'ar': {  # Arabic
                'part': ['جزء', 'قسم', 'فصل', 'باب'],
                'appendix': ['ملحق', 'مرفق', 'ضميمة'],
                'chapter': ['فصل', 'باب'],
                'introduction': ['مقدمة', 'تمهيد', 'استهلال'],
                'conclusion': ['خاتمة', 'استنتاج', 'ملخص'],
                'references': ['مراجع', 'مصادر', 'ببليوغرافيا'],
                'table_of_contents': ['فهرس المحتويات', 'المحتويات', 'فهرس']
            },
            'ko': {  # Korean
                'part': ['부', '편', '장', '제.*부', '제.*편'],
                'appendix': ['부록', '첨부', '참고자료'],
                'chapter': ['장', '제.*장', '챕터'],
                'introduction': ['서론', '도입', '개요', '머리말'],
                'conclusion': ['결론', '요약', '맺음말', '정리'],
                'references': ['참고문헌', '인용문헌', '문헌', '참조'],
                'table_of_contents': ['목차', '차례', '내용']
            },
            'ru': {  # Russian
                'part': ['часть', 'раздел', 'глава'],
                'appendix': ['приложение', 'дополнение'],
                'chapter': ['глава', 'гл'],
                'introduction': ['введение', 'предисловие', 'вступление'],
                'conclusion': ['заключение', 'выводы', 'резюме'],
                'references': ['литература', 'библиография', 'источники'],
                'table_of_contents': ['содержание', 'оглавление']
            }
        }

        # Month names in different languages for date detection
        self.month_names = {
            'en': ['january', 'february', 'march', 'april', 'may', 'june',
                   'july', 'august', 'september', 'october', 'november', 'december',
                   'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                   'jul', 'aug', 'sep', 'oct', 'nov', 'dec'],
            'ja': ['1月', '2月', '3月', '4月', '5月', '6月',
                   '7月', '8月', '9月', '10月', '11月', '12月'],
            'zh': ['一月', '二月', '三月', '四月', '五月', '六月',
                   '七月', '八月', '九月', '十月', '十一月', '十二月',
                   '1月', '2月', '3月', '4月', '5月', '6月',
                   '7月', '8月', '9月', '10月', '11月', '12月'],
            'es': ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                   'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
                   'ene', 'feb', 'mar', 'abr', 'may', 'jun',
                   'jul', 'ago', 'sep', 'oct', 'nov', 'dic'],
            'fr': ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                   'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
                   'janv', 'févr', 'mars', 'avr', 'mai', 'juin',
                   'juil', 'août', 'sept', 'oct', 'nov', 'déc'],
            'de': ['januar', 'februar', 'märz', 'april', 'mai', 'juni',
                   'juli', 'august', 'september', 'oktober', 'november', 'dezember',
                   'jan', 'feb', 'mär', 'apr', 'mai', 'jun',
                   'jul', 'aug', 'sep', 'okt', 'nov', 'dez'],
            'ar': ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                   'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'],
            'ko': ['1월', '2월', '3월', '4월', '5월', '6월',
                   '7월', '8월', '9월', '10월', '11월', '12월'],
            'ru': ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
                   'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь',
                   'янв', 'фев', 'мар', 'апр', 'май', 'июн',
                   'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
        }

        # Warning/instruction words in different languages
        self.warning_words = {
            'en': ['required', 'must', 'mandatory', 'warning', 'notice', 'important', 'attention'],
            'ja': ['必須', '必要', '注意', '警告', '重要', 'お知らせ', '義務'],
            'zh': ['必需', '必须', '必須', '注意', '警告', '重要', '通知', '强制', '強制'],
            'es': ['requerido', 'obligatorio', 'advertencia', 'aviso', 'importante', 'atención'],
            'fr': ['requis', 'obligatoire', 'avertissement', 'avis', 'important', 'attention'],
            'de': ['erforderlich', 'pflicht', 'warnung', 'hinweis', 'wichtig', 'achtung'],
            'ar': ['مطلوب', 'إجباري', 'تحذير', 'إشعار', 'مهم', 'انتباه'],
            'ko': ['필수', '필요', '주의', '경고', '중요', '알림', '의무'],
            'ru': ['обязательно', 'необходимо', 'предупреждение', 'уведомление', 'важно', 'внимание']
        }

    def detect_language(self, text: str) -> str:
        """Detect the primary language of the text."""
        if not text:
            return 'en'
        
        # Count characters from different scripts
        script_counts = {
            'latin': 0,      # English, Spanish, French, German, etc.
            'cjk': 0,        # Chinese, Japanese, Korean
            'arabic': 0,     # Arabic
            'cyrillic': 0    # Russian
        }
        
        for char in text:
            code = ord(char)
            if (0x0041 <= code <= 0x005A) or (0x0061 <= code <= 0x007A):  # Basic Latin
                script_counts['latin'] += 1
            elif (0x4E00 <= code <= 0x9FFF) or (0x3040 <= code <= 0x309F) or (0x30A0 <= code <= 0x30FF):  # CJK
                script_counts['cjk'] += 1
            elif 0x0600 <= code <= 0x06FF:  # Arabic
                script_counts['arabic'] += 1
            elif 0x0400 <= code <= 0x04FF:  # Cyrillic
                script_counts['cyrillic'] += 1
        
        # Determine primary script
        max_script = max(script_counts, key=script_counts.get)
        
        if max_script == 'cjk':
            # Further distinguish between Chinese, Japanese, Korean
            if any(0x3040 <= ord(c) <= 0x309F or 0x30A0 <= ord(c) <= 0x30FF for c in text):
                return 'ja'  # Japanese (Hiragana/Katakana)
            elif any(0xAC00 <= ord(c) <= 0xD7AF for c in text):
                return 'ko'  # Korean (Hangul)
            else:
                return 'zh'  # Chinese
        elif max_script == 'arabic':
            return 'ar'
        elif max_script == 'cyrillic':
            return 'ru'
        else:
            # For Latin scripts, use keyword detection
            text_lower = text.lower()
            for lang, keywords in self.heading_keywords.items():
                if lang in ['en', 'es', 'fr', 'de']:
                    matches = sum(1 for category in keywords.values() 
                                for keyword in category 
                                if keyword in text_lower)
                    if matches > 0:
                        return lang
            return 'en'  # Default to English

    def clean_extracted_text(self, text: str, is_heading: bool = False) -> str:
        """Clean up common PDF extraction artifacts and spacing issues."""
        if not text:
            return text
            
        # Fix specific patterns where single letters are separated from words
        # Only fix obvious cases to avoid false positives
        text = re.sub(r'\b([A-Z])\s+([a-z]{2,})\b', r'\1\2', text)  # "Y ou" -> "You" (only 2+ chars)
        text = re.sub(r'\b([A-Z])\s+([A-Z]{2,})\b', r'\1\2', text)  # "T HERE" -> "THERE" (only 2+ chars)
        
        # Fix very specific single letter cases that are clearly wrong
        text = re.sub(r'\b([a-z])\s+([a-z]{2})\b', lambda m: 
                     m.group(1) + m.group(2) if m.group(2) in ['ou', 'he', 'er', 'ed', 'ly', 'ng'] 
                     else m.group(0), text)  # Only join common suffixes
        
        # Remove multiple consecutive spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Clean up spaces around punctuation
        text = re.sub(r'\s+([!?.,;:])', r'\1', text)  # Remove space before punctuation
        text = re.sub(r'([!?.,;:])\s*([!?.,;:])', r'\1\2', text)  # Remove spaces between punctuation
        
        cleaned_text = text.strip()
        
        # Add trailing space for headings
        if is_heading and cleaned_text and not cleaned_text.endswith(' '):
            cleaned_text += ' '
        
        return cleaned_text

    def smart_deduplicate_title(self, title: str) -> str:
        """Smart deduplication: keep longest versions of words, remove single letters (except 'a'), handle substrings."""
        # print(f"[DEBUG] Before deduplication: '{title}'")
        
        # Split into words, preserving punctuation
        import re
        # Split on spaces but keep punctuation attached to words
        words = title.split()
        
        # Remove single letters except 'a' and 'A'
        words = [word for word in words if len(word.strip('.,!?:;')) > 1 or word.lower().strip('.,!?:;') == 'a']
        
        # print(f"[DEBUG] After removing single letters: {words}")
        
        # Add preserved words set
        preserved_words = {"a", "an", "of", "in", "on", "to", "by", "for", "at", "as"}
        
        # Find and remove substring duplicates
        filtered_words = []
        for i, word in enumerate(words):
            clean_word = word.strip('.,!?:;').lower()
            # Preserve certain words regardless of substring logic
            if clean_word in preserved_words:
                filtered_words.append(word)
                continue
            should_keep = True
            
            # Check if this word is a meaningful substring of any other word in the list
            for j, other_word in enumerate(words):
                if i != j:
                    clean_other = other_word.strip('.,!?:;').lower()
                    # More intelligent substring detection:
                    # 1. Current word must be meaningfully shorter 
                    # 2. Should not remove if both words are legitimate dictionary words
                    # 3. Prefer removing obvious fragments/OCR artifacts
                    if (clean_word != clean_other and 
                        clean_word in clean_other):
                        
                        # Calculate the difference in length
                        length_diff = len(clean_other) - len(clean_word)
                        
                        # For very short words (2-3 chars), be aggressive if they're clearly fragments
                        if len(clean_word) <= 3 and length_diff >= 2:
                            # Check if it's at the start or end of the longer word (likely fragment)
                            if (clean_other.startswith(clean_word) or clean_other.endswith(clean_word)):
                                # print(f"[DEBUG] Removing short fragment '{word}' of '{other_word}'")
                                should_keep = False
                                break
                        
                        # For words 4+ chars, need significant length difference
                        elif len(clean_word) >= 4 and length_diff >= 2:
                            # If the shorter word is a substantial part of the longer word, remove it
                            # Exception: only keep both if shorter word is clearly at word boundary
                            pattern = r'\b' + re.escape(clean_word) + r'\b'
                            if not re.search(pattern, clean_other):
                                # print(f"[DEBUG] Removing '{word}' because it's substring of '{other_word}'")
                                should_keep = False
                                break
            
            if should_keep:
                # Also check if we already have this word (case-insensitive)
                already_added = False
                for existing in filtered_words:
                    if existing.strip('.,!?:;').lower() == clean_word:
                        already_added = True
                        break
                
                if not already_added:
                    filtered_words.append(word)
                else:
                    # print(f"[DEBUG] Removing duplicate '{word}'")
                    pass
        
        result = " ".join(filtered_words)
        # print(f"[DEBUG] After smart deduplication: '{result}'")
        return result

    def extract_title_from_text(self, doc: fitz.Document) -> str:
        """Extract document title from the first page content, handling multi-line titles."""
        # print("[DEBUG] Starting title extraction from first page")
        if len(doc) > 0:
            page = doc[0]
            blocks = page.get_text("dict")["blocks"]
            
            # Get table bboxes for the first page to avoid extracting title from tables
            page_tables = []
            try:
                import pdfplumber
                with pdfplumber.open(doc.name) as pdf:
                    if len(pdf.pages) > 0:
                        first_page = pdf.pages[0]
                        found_tables = first_page.find_tables()
                        for table in found_tables:
                            if table.bbox:
                                # Apply same filtering as detect_tables_with_pdfplumber
                                try:
                                    extracted_rows = table.extract()
                                    # Only consider tables with 3+ rows as real tables
                                    if table.cells and extracted_rows and len(extracted_rows) >= 3:
                                        page_tables.append(table.bbox)
                                        # print(f"[DEBUG] Valid table found for title filtering: {len(extracted_rows)} rows")
                                    else:
                                        # print(f"[DEBUG] Skipping small table for title filtering: {len(extracted_rows) if extracted_rows else 0} rows")
                                        pass
                                except Exception as e:
                                    # print(f"[DEBUG] Could not extract table rows for title filtering: {e}")
                                    # If we can't extract rows, include the table to be safe
                                    page_tables.append(table.bbox)
                # print(f"[DEBUG] Found {len(page_tables)} valid tables on first page")
            except Exception as e:
                # print(f"[DEBUG] Could not detect tables for title extraction: {e}")
                pass
            
            # Find text blocks and their font sizes
            candidates = []
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        line_parts = []
                        line_size = 0
                        line_y = line["bbox"][1]
                        line_flags = 0
                        
                        for span in line["spans"]:
                            text = span["text"].strip()
                            # Filter out too short text and common non-title patterns
                            if (text and len(text) > 1 and 
                                not text.startswith(("Page ", "Chapter ", "Section ")) and
                                not text.startswith("http") and
                                not text.endswith((".com", ".org", ".net")) and
                                not re.match(r'^[0-9\-]+$', text) and  # Skip dates/numbers
                                not re.match(r'^[0-9\s]*$', text) and   # Skip page numbers
                                not re.match(r'^[a-z]\s*$', text)):     # Skip single lowercase letters
                                # Check for repetitive patterns in the text itself
                                words = text.split()
                                if len(words) <= 3 or len(set(words)) >= len(words) * 0.6:  # Avoid highly repetitive text
                                    line_parts.append(text)
                                    line_size = max(line_size, span["size"])
                                    line_flags |= span.get("flags", 0)
                        
                        # If we found valid text in this line, add it as a candidate
                        if line_parts:
                            # Check if line is right-aligned
                            line_x = line["bbox"][0]
                            page_width = page.rect.width
                            is_right_aligned = line_x > page_width * 0.6
                            
                            # Check if text is inside a table
                            line_x0, line_y0, line_x1, line_y1 = line["bbox"]
                            line_cx = (line_x0 + line_x1) / 2
                            line_cy = (line_y0 + line_y1) / 2
                            is_in_table = False
                            for table_bbox in page_tables:
                                tb_x0, tb_y0, tb_x1, tb_y1 = table_bbox
                                if tb_x0 <= line_cx <= tb_x1 and tb_y0 <= line_cy <= tb_y1:
                                    is_in_table = True
                                    # print(f"[DEBUG] Skipping title candidate in table: '{' '.join(line_parts)}'")
                                    break
                            
                            # Check if text is inside a box (form field, callout box, etc.)
                            is_in_box = self.is_text_in_box(page, line["bbox"])
                            if is_in_box:
                                # print(f"[DEBUG] Skipping title candidate in box: '{' '.join(line_parts)}'")
                                pass
                            
                            if not is_right_aligned and not is_in_table and not is_in_box and line_y < page.rect.height * 0.60:
                                candidates.append({
                                    "text": " ".join(line_parts),
                                    "size": line_size,
                                    "y": line_y,
                                    "flags": line_flags
                                })
            
            # print(f"[DEBUG] Found {len(candidates)} title candidates")
            # for i, c in enumerate(candidates):
            #     print(f"[DEBUG] Candidate {i}: '{c['text']}' (size={c['size']}, y={c['y']})")
            
            if candidates:
                # Filter out candidates that are too long
                candidates = [c for c in candidates if len(c["text"]) < 200]
                
                # Only look for titles in the top 60% of the page
                top_y = page.rect.height * 0.60
                top_candidates = [c for c in candidates if c["y"] <= top_y]
                
                if not top_candidates:
                    return ""
                
                # Group candidates by font size (within 15% tolerance)
                size_groups = {}
                for c in top_candidates:
                    size_key = round(c["size"] / 2) * 2  # Round to nearest 2 units
                    if size_key not in size_groups:
                        size_groups[size_key] = []
                    size_groups[size_key].append(c)
                
                # Look for multi-part titles: largest font + next largest that are close together
                if len(size_groups) >= 2:
                    # Sort font sizes in descending order
                    sorted_sizes = sorted(size_groups.keys(), reverse=True)
                    largest_size = sorted_sizes[0]
                    second_largest_size = sorted_sizes[1]
                    
                    # Check if second largest is reasonably close in size (within 40% of largest)
                    if second_largest_size >= largest_size * 0.6:
                        # Combine both groups and sort by position
                        all_title_candidates = size_groups[largest_size] + size_groups[second_largest_size]
                        all_title_candidates.sort(key=lambda x: x["y"])
                        
                        # Group into lines that are close together
                        title_lines = []
                        for c in all_title_candidates:
                            # Check if we're still in the title area (top 50% of page)
                            if c["y"] > page.rect.height * 0.5:
                                break
                                
                            # Find if this candidate is close to existing lines
                            added_to_line = False
                            for line_group in title_lines:
                                last_y = line_group[-1]["y"]
                                # If within 3x the larger font size vertically
                                if abs(c["y"] - last_y) <= largest_size * 3:
                                    line_group.append(c)
                                    added_to_line = True
                                    break
                            
                            if not added_to_line:
                                title_lines.append([c])
                        
                        # Combine all title parts
                        title_parts = []
                        for line_group in title_lines:
                            line_text = " ".join([c["text"].strip() for c in line_group if c["text"].strip()])
                            if line_text:
                                title_parts.append(line_text)
                        
                        if title_parts:
                            combined_title = " ".join(title_parts)
                            final_title = self.smart_deduplicate_title(combined_title)
                            # final_title = self.clean_extracted_text(final_title)
                            # print(f"[DEBUG] Multi-part title selected: '{final_title}'")
                            return final_title
                
                # Fallback to single largest font size group
                largest_size = max(size_groups.keys())
                largest_group = size_groups[largest_size]
                
                # Sort by y-position
                largest_group.sort(key=lambda x: x["y"])
                
                # Combine lines that are close together (within 3x font size)
                combined_lines = []
                for c in largest_group:
                    if not combined_lines:
                        combined_lines.append([c])
                    else:
                        last_group = combined_lines[-1]
                        last_y = last_group[-1]["y"]
                        if c["y"] - last_y <= largest_size * 3:
                            last_group.append(c)
                        else:
                            combined_lines.append([c])
                
                # Create title from the first (topmost) group
                if combined_lines:
                    # Use the first group (topmost on page) instead of longest
                    best_group = combined_lines[0]
                    # Take only unique, non-repeating text parts
                    seen_texts = set()
                    unique_parts = []
                    for c in best_group:
                        text = c["text"].strip()
                        if text and text not in seen_texts and len(text) > 2:
                            unique_parts.append(text)
                            seen_texts.add(text)
                    
                    if unique_parts:
                        # Apply smart deduplication
                        final_title = self.smart_deduplicate_title(" ".join(unique_parts))
                        # final_title = self.clean_extracted_text(final_title)
                        # print(f"[DEBUG] Selected title: '{final_title}'")
                        return final_title
                
            return ""
        
        return "Untitled Document"
    
    def is_heading_by_formatting(self, span: Dict, avg_font_size: float) -> Optional[str]:
        """Determine heading level based on formatting characteristics."""
        font_size = span.get("size", 0)
        flags = span.get("flags", 0)
        
        # Check if text is bold (flag 16) or larger than average
        is_bold = bool(flags & 16)
        size_ratio = font_size / avg_font_size if avg_font_size > 0 else 1
        
        # Debug output for heading detection
        # print(f"[DEBUG] Span formatting: size={font_size}, avg_size={avg_font_size}, ratio={size_ratio:.2f}, is_bold={is_bold}, flags={flags}")
        
        # More lenient heading detection logic
        if size_ratio >= 1.4 or (is_bold and size_ratio >= 1.2):
            return "H1"
        elif size_ratio >= 1.20 or (is_bold and size_ratio >= 1.0):
            return "H2"
        elif is_bold and size_ratio >= 0.8:
            return "H3"
        
        return None
    
    def get_text_rotation(self, span: Dict) -> float:
        """Calculate text rotation angle in degrees from transformation matrix."""
        try:
            matrix = span.get("transform", None)
            if not matrix or len(matrix) < 4:
                return 0.0
            
            a, b, c, d = matrix[:4]
            
            # Calculate rotation angle in radians
            # For a rotation matrix: [cos θ, -sin θ, sin θ, cos θ]
            # θ = atan2(sin θ, cos θ) = atan2(c, a)
            import math
            angle = math.atan2(c, a)
            degrees = math.degrees(angle)
            
            # Normalize angle to 0-360 range
            degrees = (degrees + 360) % 360
            return degrees
            
        except (KeyError, IndexError, TypeError):
            return 0.0
    
    def is_text_direction_compatible(self, text: str, x_position: float, page_width: float) -> bool:
        """Check if text direction is compatible with the detected language."""
        detected_lang = self.detect_language(text)
        
        # For right-to-left languages (Arabic), text should be on the right side
        if detected_lang == 'ar':
            return x_position > page_width * 0.3  # Allow right and center positioning
        
        # For left-to-right languages, text should be on the left side
        return x_position < page_width * 0.7  # Allow left and center positioning

    def is_text_tilted(self, span: Dict) -> bool:
        """Check if text is tilted/rotated."""
        angle = self.get_text_rotation(span)
        
        # Consider text tilted if it's rotated more than 5 degrees
        # But allow text that's close to common angles (0°, 90°, 180°, 270°)
        tolerance = 5.0
        for base_angle in [0, 90, 180, 270]:
            if abs((angle - base_angle + 180) % 360 - 180) <= tolerance:
                return False
                
        return True
    
    def should_skip_text(self, text: str, spans: List[Dict] = None) -> bool:
        """Check if text should be skipped (addresses, form fields, websites, etc.) with multilingual support."""
        
        if not text or not text.strip():
            return True
        
        # Detect language
        detected_lang = self.detect_language(text)
        
        # Enhanced table of contents detection
        toc_patterns = [
            r'.*\.{3,}.*',  # Table of contents entries with multiple dots (e.g., "Introduction ........ 5")
            r'.*\.{2,}\s*\d+\s*$',  # Text ending with dots followed by page numbers
            r'.*\s+\.+\s*\d+\s*$',  # Text with dots and page numbers at end
            r'.*\s+\d+\s*$',  # Text ending with standalone page numbers (common in TOC)
        ]
        
        # Build multilingual warning patterns
        warning_patterns = []
        
        # Add warning words for detected language and English as fallback
        languages_to_check = [detected_lang, 'en'] if detected_lang != 'en' else ['en']
        
        for lang in languages_to_check:
            if lang in self.warning_words:
                warning_words = '|'.join(re.escape(word) for word in self.warning_words[lang])
                warning_patterns.extend([
                    rf'.*(?:{warning_words}).*',  # Warning text
                    rf'.*(?:{"鞋|衣服|着装" if lang == "zh" else "靴|服装" if lang == "ja" else "shoes?|clothing|dress code|attire"}).*(?:{warning_words}).*',  # Dress code requirements
                ])
        
        # Universal patterns (less language-dependent)
        universal_patterns = [
            r'.*\.COM\b.*',  # Website references
            r'.*WWW\..*',  # Website URLs
            r'.*@.*\..*',    # Email addresses
            r'^[A-Z\s]+(?:REQUIRED|MUST|SHOULD|PLEASE|VISIT).*',  # All caps instructions (keeping English for international docs)
        ]
        warning_patterns.extend(universal_patterns)
        
        # Check for table of contents patterns first
        for pattern in toc_patterns:
            if re.match(pattern, text.strip()):
                # Allow "Table of Contents" itself and appendix headings in any language
                toc_keywords = []
                appendix_keywords = []
                
                for lang in languages_to_check:
                    if lang in self.heading_keywords:
                        toc_keywords.extend(self.heading_keywords[lang]['table_of_contents'])
                        appendix_keywords.extend(self.heading_keywords[lang]['appendix'])
                
                # Build pattern for table of contents and appendix detection
                toc_pattern = '|'.join(re.escape(keyword) for keyword in toc_keywords)
                appendix_pattern = '|'.join(re.escape(keyword) for keyword in appendix_keywords)
                
                if not re.match(rf'^(?:{toc_pattern}|{appendix_pattern}\s+[A-Z0-9]+:).*$', text.strip(), re.IGNORECASE):
                    return True
        
        # Check for warning/informational text patterns
        for pattern in warning_patterns:
            if re.match(pattern, text.strip(), re.IGNORECASE):
                return True
        
        # Multilingual date patterns
        date_patterns = self.build_multilingual_date_patterns(detected_lang)
        
        # Additional check: if text is very long and instructional, likely not a heading
        if len(text) > 60:
            instruction_words = []
            for lang in languages_to_check:
                if lang in self.warning_words:
                    instruction_words.extend(self.warning_words[lang])
            
            if any(word in text.upper() for word in instruction_words):
                return True
        
        # First check if this looks like a numbered heading - if so, check if it's bold AND has no dots
        if re.match(r'^\d+\.\s+[A-Z\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', text.strip()):
            # Skip if it contains multiple dots (table of contents entry)
            if re.search(r'\.{3,}', text):
                return True  # Skip table of contents entries with dots
            
            # If we have span information, check if the main text (after number) is bold
            if spans:
                # Find spans that contain the main text (not just the number)
                main_text_bold = False
                for span in spans:
                    span_text = span.get("text", "").strip()
                    if span_text:
                        # If this span contains letters (including CJK characters), check if it's bold
                        if re.search(r'[A-Za-z\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af\u0600-\u06ff\u0400-\u04ff]', span_text):
                            flags = span.get("flags", 0)
                            is_bold = bool(flags & 16)
                            if is_bold:
                                main_text_bold = True
                                break
                
                if main_text_bold:
                    return False  # Don't skip if main text is bold (it's a heading)
                # If main text not bold, continue to check if it should be skipped as a list
            else:
                # If no span info available, assume it's a heading (fallback)
                return False
            
        # Address patterns (mostly universal but some language-specific)
        address_patterns = [
            r'^\d+\s+[A-Za-z\s\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]+(?:street|st\b|avenue|ave\b|road|rd\b|drive|dr\b|lane|ln\b|parkway|pkwy|boulevard|blvd\b|街|路|町|丁目)',
            r'^[A-Z]{2}\s+\d{5}(?:-\d{4})?$',
            r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2}\s+\d{5}$',
            r'^(?:Suite|Ste|Apt|Unit|Building|Bldg|Floor|Fl|号室|階)\b.*\d+',
        ]
        
        # Form field patterns (multilingual)
        form_patterns = [
            r'^[_\-]{3,}$',  # Lines of underscores or dashes
            r'^\s*(?:RSVP|Name|Date|Time|Phone|Email|Address|Sign|Signature|Title|Age|名前|日付|時間|電話|メール|住所|署名|タイトル|年齢|姓名|日期|时间|电话|邮箱|地址|签名|标题|年龄)[\s:]*[_\-]*$',
            r'^\s*(?:Signature\s+of\s+\w+|署名者|签名者).*$',  # "Signature of [title]" patterns
            r'^\s*(?:Yes|No|Maybe|はい|いいえ|たぶん|是|否|也许)[\s:]*$',  # Common form options
            r'.*[_]{3,}.*',  # Any text containing multiple underscores
            r'.*[\-]{3,}.*',  # Any text containing multiple dashes
            r'^(?:S\.?No\.?|Sl\.?No\.?|Sr\.?No\.?|Serial\s*No\.?|Serial\s*Number|番号|序号)[\s:]*$',  # Serial number headers
            r'^\d+\.\s*(?:Amount|Name|Address|Details?|Signature|金額|名前|住所|詳細|署名|金额|姓名|地址|详情|签名).*$',  # Numbered form fields
            r'^(?:Relationship|Amount|Signature|Details?|関係|金額|署名|詳細|关系|金额|签名|详情)[\s:]*$',  # Common form field labels
            r'^[.\s]{5,}$',  # Lines of dots (table of contents separators)
            r'^\.{5,}$',  # Lines of consecutive dots
            r'^\s*\.+\s*$',  # Any line that's mostly or all dots
            r'.*\.{3,}.*',  # Table of contents entries with multiple dots
            # Bullet points and list items (including CJK bullets)
            r'^\s*[•·▪▫■□○●◦‣⁃・※]\s+',  # Various bullet point symbols including Japanese
            r'^\s*[-*+]\s+',  # Dash, asterisk, plus bullet points
            r'^\s*\d+[\.\)]\s+[a-z][a-z]',  # Numbered lists with at least 2 lowercase letters
            r'^\s*[a-zA-Z][\.\)]\s+',  # Lettered lists (a. or a))
            r'^\s*[ivxlcdm]+[\.\)]\s+',  # Roman numeral lists
            r'^\s*\([a-zA-Z0-9]+\)\s+',  # Parenthetical lists
            # Text fragments that shouldn't be headings
            r'.*\s+\.\s*\*\s*$',  # Text ending with . *
            r'^[a-z].*\s+\.$',  # Lowercase text ending with period (sentence fragments)
            r'^\s*(?:the|this|these|that|those|これ|その|あの|この|该|这|那)\s+',  # Text starting with articles/demonstratives
            r'.*\s+(?:years?|年|年間|岁|歲)\s*[\.\*]*$',  # Text ending with "year" or "years"
            r'^.*\s+(?:and|or|と|または|和|或者)\s*$',  # Text ending with conjunctions
            r'^.*\s+(?:of|in|to|for|with|by|at|on|の|に|で|から|へ|的|在|到|为|和|由|在)\s*$',  # Text ending with prepositions
        ]
        
        # Website and contact patterns
        web_patterns = [
            r'^(?:https?:\/\/)?(?:www\.)?[a-zA-Z0-9\-\.]+\.(?:com|org|net|edu|gov|mil|biz|info|io|co|uk|us|jp|cn|kr)/?.*$',
            r'^.*\.(?:com|org|net|edu|gov|mil|biz|info|io|co|uk|us|jp|cn|kr)\s*$',
            r'^(?:Email|Website|URL|Web|WWW|メール|ウェブサイト|网站|웹사이트)[:\s].*$',
        ]

        # Check all patterns
        all_patterns = address_patterns + form_patterns + web_patterns + date_patterns
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in all_patterns)

    def build_multilingual_date_patterns(self, language: str) -> List[str]:
        """Build date patterns for the detected language."""
        patterns = []
        
        # Universal numeric date patterns
        patterns.extend([
            r'^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\.?$',  # DD/MM/YYYY or MM/DD/YYYY
            r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}\.?$',  # YYYY/MM/DD
            r'^\d{1,2}\s+\d{1,2}\s+\d{4}\.?$',  # DD MM YYYY
        ])
        
        # Language-specific month patterns
        if language in self.month_names:
            months = '|'.join(re.escape(month) for month in self.month_names[language])
            patterns.extend([
                rf'^\d{{1,2}}\s+(?:{months})\s+\d{{4}}\.?$',  # DD Month YYYY
                rf'^(?:{months})\s+\d{{1,2}},?\s+\d{{4}}\.?$',  # Month DD, YYYY
                rf'^(?:{months})\s+\d{{4}}\.?$',  # Month YYYY
            ])
        
        # Add English patterns as fallback for international documents
        if language != 'en' and 'en' in self.month_names:
            en_months = '|'.join(re.escape(month) for month in self.month_names['en'])
            patterns.extend([
                rf'^\d{{1,2}}\s+(?:{en_months})\s+\d{{4}}\.?$',
                rf'^(?:{en_months})\s+\d{{1,2}},?\s+\d{{4}}\.?$',
                rf'^(?:{en_months})\s+\d{{4}}\.?$',
            ])
        
        return patterns

    def is_heading_by_pattern(self, text: str) -> Optional[str]:
        """Detect headings using text patterns with multilingual support."""
        text = text.strip()
        
        # Skip if text should not be included in outline
        if self.should_skip_text(text, None):
            return None
        
        # Detect language
        detected_lang = self.detect_language(text)
        
        # Build multilingual heading patterns
        h1_patterns = []
        h2_patterns = []
        h3_patterns = []
        
        # Add patterns for detected language and English as fallback
        languages_to_check = [detected_lang, 'en'] if detected_lang != 'en' else ['en']
        
        for lang in languages_to_check:
            if lang in self.heading_keywords:
                keywords = self.heading_keywords[lang]
                
                # H1 patterns
                part_words = '|'.join(re.escape(word) for word in keywords['part'])
                chapter_words = '|'.join(re.escape(word) for word in keywords['chapter'])
                h1_patterns.extend([
                    rf'^({part_words})\s+[IVX\d]+',  # Part/章 + Roman/Arabic numerals
                    rf'^({chapter_words})\s+\d+',    # Chapter/章 + numbers
                    rf'^chapter\s+\d+',              # chapter X (English)
                    rf'^第\d+章',                     # 第X章 (Japanese/Chinese)
                    rf'^第\d+部',                     # 第X部 (Japanese/Chinese)
                    rf'^글\d+장',                     # 글X장 (Korean alternative)
                    rf'^глава\s+\d+',                # глава X (Russian)
                    rf'^часть\s+[IVX\d]+',           # часть I/1 (Russian)
                    rf'^kapitel\s+\d+',              # kapitel X (German)
                    rf'^teil\s+[IVX\d]+',            # teil I/1 (German)
                    rf'^capítulo\s+\d+',             # capítulo X (Spanish)
                    rf'^parte\s+[IVX\d]+',           # parte I/1 (Spanish)
                    rf'^chapitre\s+\d+',             # chapitre X (French)
                    rf'^partie\s+[IVX\d]+',          # partie I/1 (French)
                    rf'^فصل\s+\d+',                  # فصل X (Arabic)
                    rf'^جزء\s+\d+',                  # جزء X (Arabic)
                    rf'^제\d+장',                      # 제X장 (Korean)
                    rf'^제\d+부',                      # 제X부 (Korean)
                    r'^[A-Z\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af\s]{10,}$',  # All caps/CJK text
                    r'^\d+\.\s+[A-Z\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]',  # 1. Introduction
                    r'^[A-Z\u4e00-\u9fff][A-Z\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af\s]+[A-Z\u4e00-\u9fff]$',  # Multiple caps words/CJK
                ])
                
                # H2 patterns
                appendix_words = '|'.join(re.escape(word) for word in keywords['appendix'])
                h2_patterns.extend([
                    rf'^({appendix_words})\s+[A-Z0-9]+:',  # Appendix/付録 A: or Appendix/付録 1:
                    rf'^({appendix_words})\s*[A-Z0-9]+',   # Appendix/付録 A or Appendix/付録 1 (no colon)
                    rf'^付録[A-Z0-9]',                      # 付録A (Japanese)
                    rf'^附录[A-Z0-9]',                      # 附录A (Chinese)
                    rf'^приложение\s+[A-ZА-Я0-9]',         # приложение А (Russian)
                    rf'^anhang\s+[A-Z0-9]',                # anhang A (German)
                    rf'^apéndice\s+[A-Z0-9]',              # apéndice A (Spanish)
                    rf'^annexe\s+[A-Z0-9]',                # annexe A (French)
                    rf'^ملحق\s+[A-Z0-9]',                  # ملحق A (Arabic)
                    rf'^부록\s*[A-Z0-9]',                   # 부록A (Korean)
                    r'^\d+\.\d+\s+',    # 1.1 Subsection
                    r'^[A-Z\u4e00-\u9fff][a-z\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]+(\s+[A-Z\u4e00-\u9fff][a-z\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]+)*:$',  # Title Case:
                    r'^\d+\s+[A-Z\u4e00-\u9fff]',    # 1 Introduction
                    r'^[A-Z\u4e00-\u9fff][a-z\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]+(\s+[A-Z\u4e00-\u9fff][a-z\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]+)*$',  # Title Case without colon
                ])
        
        # H3 patterns (universal)
        h3_patterns = [
            r'^\d+\.\d+\.\d+\s+',  # 1.1.1 Sub-subsection
            r'^[a-z]\)\s+',        # a) bullet point
            r'^[•·▪▫■□○●◦‣⁃・※]\s+[A-Z\u4e00-\u9fff]',  # • Bullet point (including CJK bullets)
            r'^[(（][a-zA-Z0-9]+[)）]\s+',  # (a) or (1) style
        ]
        
        # Check patterns
        for pattern in h1_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return "H1"
        
        for pattern in h2_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return "H2"
                
        for pattern in h3_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return "H3"
        
        # Check single word patterns for H2 - but be more restrictive
        # Only classify single words as headings if they are very specific patterns
        restrictive_single_word_patterns = [
            r'^[A-Z]{4,}$',           # Single ALL CAPS word (like "OVERVIEW", "INTRODUCTION")
            r'^[\u4e00-\u9fff]{2,}$',  # Single CJK word/phrase (2+ characters)
            r'^[\u3040-\u309f\u30a0-\u30ff]{3,}$',  # Single Hiragana/Katakana word (3+ characters)
            r'^[\uac00-\ud7af]{2,}$',  # Single Korean word (2+ characters)
        ]
        
        for pattern in restrictive_single_word_patterns:
            if re.match(pattern, text) and len(text) >= 3:  # At least 3 chars for single words
                return "H2"
        
        return None
    
    def is_likely_list_item(self, line_text: str, lines: List[Dict], current_index: int) -> bool:
        """
        Check if a numbered item (like 9.1 something) is likely part of a list sequence
        rather than a standalone heading.
        
        Args:
            line_text: The text to check
            lines: All lines in the current block
            current_index: Index of the current line being checked
            
        Returns:
            True if this appears to be part of a numbered list sequence
        """
        # Only check items that match numbered subsection pattern (e.g., "9.1 something")
        if not re.match(r'^\d+\.\d+\s+', line_text.strip()):
            return False
            
        # Extract the number pattern (e.g., "9.1" from "9.1 something")
        match = re.match(r'^(\d+)\.(\d+)\s+', line_text.strip())
        if not match:
            return False
            
        major_num = int(match.group(1))
        minor_num = int(match.group(2))
        
        # Look for similar patterns in nearby text (within 5 lines before/after)
        similar_patterns = 0
        search_range = 10
        found_patterns = []  # Track all found patterns for debugging
        
        # Check previous lines in the same block
        for check_i in range(max(0, current_index - search_range), current_index):
            if check_i < len(lines):
                check_line = lines[check_i]
                check_text = ""
                for check_span in check_line["spans"]:
                    check_text += check_span["text"].strip() + " "
                check_text = check_text.strip()
                
                # Skip empty lines but continue searching
                if not check_text:
                    continue
                
                # Look for same major number with different minor numbers
                check_match = re.match(r'^(\d+)\.(\d+)\s+', check_text)
                if check_match and int(check_match.group(1)) == major_num:
                    similar_patterns += 1
                    found_patterns.append(f"{check_match.group(1)}.{check_match.group(2)} - {check_text[:50]}...")
        
        # Check following lines in the same block
        for check_i in range(current_index + 1, min(len(lines), current_index + search_range + 1)):
            check_line = lines[check_i]
            check_text = ""
            for check_span in check_line["spans"]:
                check_text += check_span["text"].strip() + " "
            check_text = check_text.strip()
            
            # Skip empty lines but continue searching
            if not check_text:
                continue
            
            # Look for same major number with different minor numbers
            check_match = re.match(r'^(\d+)\.(\d+)\s+', check_text)
            if check_match and int(check_match.group(1)) == major_num:
                similar_patterns += 1
                found_patterns.append(f"{check_match.group(1)}.{check_match.group(2)} - {check_text[:50]}...")
        
        # If we find 2+ similar patterns, it's likely a list
        is_list = similar_patterns >= 2
        if is_list:
            # print(f"[LIST DETECTED] '{line_text}' (found {similar_patterns} similar patterns)")
            # print(f"[LIST ITEMS] All patterns found:")
            # for pattern in found_patterns:
            #     print(f"  - {pattern}")
            # Store for summary
            self.detected_lists.append({
                'text': line_text,
                'pattern_count': similar_patterns,
                'patterns': found_patterns
            })
        else:
            # print(f"[LIST CHECK] '{line_text}' - Not a list (found {similar_patterns} patterns, need 2+)")
            pass
        
        return is_list

    def calculate_average_font_size(self, doc: fitz.Document) -> float:
        """Calculate average font size across the document."""
        font_sizes = []
        
        for page_num in range(min(5, len(doc))):  # Sample first 5 pages
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            if span["text"].strip():
                                font_sizes.append(span["size"])
        
        return sum(font_sizes) / len(font_sizes) if font_sizes else 12
    
    def is_text_in_box(self, page: fitz.Page, line_bbox: tuple) -> bool:
        """Check if text appears to be inside a form field box or callout box."""
        try:
            # Get drawing paths on the page
            paths = page.get_drawings()
            
            line_x0, line_y0, line_x1, line_y1 = line_bbox
            line_center_x = (line_x0 + line_x1) / 2
            line_center_y = (line_y0 + line_y1) / 2
            
            # Look for rectangular paths that could be form fields or callout boxes
            for path in paths:
                if 'rect' in path and path['rect']:
                    rect = path['rect']
                    # Check if text center is inside this rectangle
                    if (rect.x0 <= line_center_x <= rect.x1 and 
                        rect.y0 <= line_center_y <= rect.y1):
                        # Be more selective: only consider it a "box" if:
                        # 1. It's relatively small (likely a form field)
                        # 2. Or it has specific characteristics of a callout box
                        rect_width = rect.x1 - rect.x0
                        rect_height = rect.y1 - rect.y0
                        
                        # Small boxes (likely form fields)
                        if 200 < rect_width < 600 and 50 < rect_height < 700:
                            return True
                        
            
            return False
        except Exception:
            return False

    def detect_tables_with_pdfplumber(self, pdf_path: str) -> list:
        """Detect tables in a PDF using pdfplumber. Returns a list of tables with page number and bbox."""
        tables = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    found_tables = page.find_tables()
                    for idx, table in enumerate(found_tables):
                        # Use table.extract() to get rows as lists of strings
                        try:
                            extracted_rows = table.extract()
                        except Exception as e:
                            self.logger.warning(f"[pdfplumber] Table {idx}: extract() failed: {e}")
                            continue

                        if not table.cells or len(extracted_rows) < 3:
                            continue  # not a real table

                        tables.append({
                            "page": page_num + 1,
                            "bbox": table.bbox,  # (x0, top, x1, bottom)
                            "table_index": idx
                        })
        except Exception as e:
            self.logger.error(f"Error detecting tables in {pdf_path}: {e}")
        return tables
        
    def extract_outline(self, pdf_path: str) -> Dict[str, Any]:
        """Extract outline from PDF file."""
        self.logger.info(f"Processing PDF: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            title = self.extract_title_from_text(doc)
            avg_font_size = self.calculate_average_font_size(doc)

            # Detect tables using pdfplumber (get all table bboxes per page)
            tables_by_page = {}
            for t in self.detect_tables_with_pdfplumber(pdf_path):
                page = t["page"]
                bbox = t["bbox"]
                if page not in tables_by_page:
                    tables_by_page[page] = []
                tables_by_page[page].append(bbox)

            outline = []
            processed_texts = set()  # Avoid duplicates

            for page_num in range(len(doc)):
                page = doc[page_num]
                blocks = page.get_text("dict")["blocks"]

                # Get table bboxes for this page (pdfplumber uses 1-based page numbers)
                page_tables = tables_by_page.get(page_num + 1, [])

                for block in blocks:
                    if "lines" in block:
                        lines = block["lines"]
                        i = 0
                        while i < len(lines):
                            line = lines[i]
                            line_text = ""
                            line_spans = []

                            for span in line["spans"]:
                                text = span["text"].strip()
                                if text:
                                    angle = self.get_text_rotation(span)
                                    # Accept text at normal orientation or at 90/180/270 degrees
                                    if any(abs((angle - base) % 360) <= 5.0 for base in [0, 90, 180, 270]):
                                        line_text += text + " "
                                        line_spans.append(span)

                            # Try merging with next line if formatting is similar
                            while i + 1 < len(lines):
                                next_line = lines[i + 1]
                                next_spans = next_line["spans"]
                                next_text = " ".join([s["text"].strip() for s in next_spans if s["text"].strip()])
                                if not next_text:
                                    break

                                # Check font size similarity and vertical proximity
                                font_sizes = [s["size"] for s in line_spans] or [0]
                                next_font_sizes = [s["size"] for s in next_spans] or [0]
                                if font_sizes and next_font_sizes:
                                    avg_size = sum(font_sizes) / len(font_sizes)
                                    next_avg_size = sum(next_font_sizes) / len(next_font_sizes)
                                    size_diff = abs(avg_size - next_avg_size)
                                    vertical_diff = abs(next_line["bbox"][1] - line["bbox"][3])
                                    if size_diff <= 1.0 and vertical_diff <= avg_size * 1.5:
                                        line_text += next_text + " "
                                        line_spans.extend(next_spans)
                                        i += 1
                                    else:
                                        break
                                else:
                                    break


                            line_text = line_text.strip()
                            i += 1

                            # Clean up text extraction artifacts
                            if line_text:
                                line_text = self.clean_extracted_text(line_text)

                            # DEBUG: Print line and span info
                            # print(f"[DEBUG] Checking line: '{line_text}' (page={page_num+1}, spans={len(line_spans)})")

                            # Calculate position relative to page width and check text direction compatibility
                            if line_spans:
                                line_x = line["bbox"][0]  # x-coordinate of the line
                                page_width = page.rect.width
                                is_direction_compatible = self.is_text_direction_compatible(line_text, line_x, page_width)
                                # Traditional right-aligned check for general layout
                                is_right_aligned = line_x > page_width * 0.6

                                # Check if text is inside a box
                                is_in_box = self.is_text_in_box(page, line["bbox"])

                                # Check if text is inside a table (using pdfplumber bboxes)
                                line_x0, line_y0, line_x1, line_y1 = line["bbox"]
                                line_cx = (line_x0 + line_x1) / 2
                                line_cy = (line_y0 + line_y1) / 2
                                is_in_table = False
                                for table_bbox in page_tables:
                                    tb_x0, tb_y0, tb_x1, tb_y1 = table_bbox
                                    if tb_x0 <= line_cx <= tb_x1 and tb_y0 <= line_cy <= tb_y1:
                                        is_in_table = True
                                        break
                            else:
                                is_direction_compatible = True
                                is_right_aligned = False
                                is_in_box = False
                                is_in_table = False

                            # Check if this line exactly matches the title or is part of title (only on first page)
                            is_title_related = False
                            if page_num == 0 and title:
                                # On first page, check for exact match or if line is part of title
                                is_exact_match = (line_text.strip().lower() == title.strip().lower())
                                # Check if line text is a significant part of the title
                                title_words = set(title.lower().split())
                                line_words = set(line_text.lower().split())
                                if title_words and line_words:
                                    # If line contains words that are in title and line is short enough to be title part
                                    word_overlap = len(title_words.intersection(line_words))
                                    is_title_part = (word_overlap >= len(line_words) and len(line_words) <= 3)
                                    is_title_related = is_exact_match or is_title_part

                            if (len(line_text) > 3 and len(line_text) < 200 and
                                line_text not in processed_texts and line_spans and
                                not self.should_skip_text(line_text, line_spans) and
                                line_text != title and
                                not is_title_related and
                                is_direction_compatible and  # Use multilingual text direction check
                                not is_in_box and
                                not is_in_table):  # Skip text inside boxes or tables

                                # Special handling for table of contents pages (multilingual)
                                # If we're on a page that contains "Table of Contents", be more selective
                                is_on_toc_page = False
                                if page_num < len(doc):
                                    page_text = page.get_text().lower()
                                    # Check for TOC keywords in multiple languages
                                    detected_lang = self.detect_language(page_text)
                                    languages_to_check = [detected_lang, 'en'] if detected_lang != 'en' else ['en']
                                    
                                    for lang in languages_to_check:
                                        if lang in self.heading_keywords:
                                            toc_keywords = self.heading_keywords[lang]['table_of_contents']
                                            if any(keyword.lower() in page_text for keyword in toc_keywords):
                                                is_on_toc_page = True
                                                break

                                # On TOC pages, only allow the actual "Table of Contents" heading
                                if is_on_toc_page:
                                    # Build multilingual TOC pattern
                                    toc_keywords = []
                                    for lang in languages_to_check:
                                        if lang in self.heading_keywords:
                                            toc_keywords.extend(self.heading_keywords[lang]['table_of_contents'])
                                    
                                    toc_pattern = '|'.join(re.escape(keyword) for keyword in toc_keywords)
                                    
                                    # Only allow "Table of Contents" itself as a heading on TOC pages
                                    if not re.match(rf'^(?:{toc_pattern})$', line_text.strip(), re.IGNORECASE):
                                        # Skip everything else on TOC pages except major section headers
                                        # Allow numbered sections that start with digits (1., 2., etc.) if they're bold
                                        if not (re.match(r'^\d+\.', line_text.strip()) and any(bool(span.get("flags", 0) & 16) for span in line_spans)):
                                            continue

                                # Require: if any span is bold, all must be bold for heading detection
                                heading_level = None
                                any_bold = any(bool(span.get("flags", 0) & 16) for span in line_spans)
                                all_bold = all(bool(span.get("flags", 0) & 16) for span in line_spans)
                                # print(f"[DEBUG] Bold analysis: any_bold={any_bold}, all_bold={all_bold} for '{line_text}'")
                                if any_bold and not all_bold:
                                    # print(f"[DEBUG] Skipped: Some but not all spans are bold in '{line_text}'")
                                    pass
                                else:
                                    for span in line_spans:
                                        level = self.is_heading_by_formatting(span, avg_font_size)
                                        if level:
                                            heading_level = level
                                            # print(f"[DEBUG] Formatting-based heading detected: '{line_text}' as {level}")
                                            break

                                # Check pattern-based heading detection
                                if not heading_level:
                                    pattern_level = self.is_heading_by_pattern(line_text)
                                    if pattern_level:
                                        # print(f"[DEBUG] Pattern-based heading detected: '{line_text}' as {pattern_level}")
                                        heading_level = pattern_level
                                    else:
                                        # print(f"[DEBUG] Skipped block: '{line_text}' (did not match formatting or pattern)")
                                        pass

                                if heading_level:
                                    # Check if this appears to be part of a numbered list sequence
                                    # print(f"[DEBUG] Checking if '{line_text}' is a list item...")
                                    if self.is_likely_list_item(line_text, lines, i):
                                        # print(f"[DEBUG] Skipping list item: '{line_text}'")
                                        pass
                                    else:
                                        # print(f"[DEBUG] Accepted heading: '{line_text}' as {heading_level} (page={page_num+1})")
                                        if page_num == 0:
                                            bold_found = any(bool(span.get("flags", 0) & 16) for span in line_spans)
                                            max_font_size = max(span.get("size", 0) for span in line_spans) if line_spans else 0
                                            if not bold_found and max_font_size >= 16:
                                                # print(f"[DEBUG] Skipped heading on first page: '{line_text}' (not bold, size={max_font_size})")
                                                continue
                                        # Clean the heading text with trailing space
                                        heading_text = self.clean_extracted_text(line_text, is_heading=True)
                                        outline.append({
                                            "level": heading_level,
                                            "text": heading_text,
                                            "page": page_num + 1
                                        })
                                        processed_texts.add(line_text)

            # Store document length before closing
            doc_length = len(doc)
            doc.close()

            # Sort outline by page number and remove duplicates
            unique_outline = []
            seen = set()
            for item in sorted(outline, key=lambda x: (x["page"], x["text"])):
                key = (item["level"], item["text"])
                if key not in seen:
                    unique_outline.append(item)
                    seen.add(key)

            # Keep title if it exists and isn't "Untitled Document", and add trailing space
            if title and title != "Untitled Document":
                title_text = self.clean_extracted_text(title, is_heading=True)
            else:
                title_text = ""

            result = {
                "title": title_text,
                "outline": unique_outline
            }

            # Print summary of detected lists
            # if self.detected_lists:
            #     print(f"\n[LIST SUMMARY] Detected {len(self.detected_lists)} numbered list sequences:")
            #     for i, list_info in enumerate(self.detected_lists, 1):
            #         print(f"  {i}. '{list_info['text']}' ({list_info['pattern_count']} patterns)")
            #         for pattern in list_info['patterns']:
            #             print(f"     - {pattern}")
            # else:
            #     print(f"\n[LIST SUMMARY] No numbered list sequences detected")

            self.logger.info(f"Extracted {len(unique_outline)} headings from {doc_length} pages")
            return result

        except Exception as e:
            self.logger.error(f"Error processing {pdf_path}: {str(e)}")
            return {
                "title": "",
                "outline": []
            }
    
    def process_directory(self, input_path: str, output_path: str):
        """Process PDF file(s) from input path."""
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        # Create output directory if it doesn't exist
        if output_path.suffix != '.json':
            output_path.mkdir(parents=True, exist_ok=True)
        
        # Handle both single file and directory inputs
        if input_path.is_file() and input_path.suffix.lower() == '.pdf':
            pdf_files = [input_path]
        else:
            pdf_files = list(input_path.glob("*.pdf"))
            
        if not pdf_files:
            self.logger.warning(f"No PDF files found at {input_path}")
            return
        
        self.logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        for pdf_file in pdf_files:
            try:
                # Extract outline
                result = self.extract_outline(str(pdf_file))
                
                # Handle output path
                if output_path.suffix == '.json':
                    output_file = output_path
                else:
                    output_filename = pdf_file.stem + ".json"
                    output_file = output_path / output_filename
                
                # Create parent directory if needed
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Save JSON result
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                self.logger.info(f"Saved outline to {output_file}")
                
            except Exception as e:
                self.logger.error(f"Failed to process {pdf_file}: {str(e)}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Extract PDF outline structure")
    parser.add_argument("--input", default="/app/input", 
                       help="Input directory containing PDF files")
    parser.add_argument("--output", default="/app/output",
                       help="Output directory for JSON files")
    
    args = parser.parse_args()
    
    extractor = PDFOutlineExtractor()
    extractor.process_directory(args.input, args.output)


if __name__ == "__main__":
    main()