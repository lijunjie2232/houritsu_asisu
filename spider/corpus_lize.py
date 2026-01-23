import json
import os
from traceback import print_exc
from typing import Any, Dict, List
from pathlib import Path


def extract_all_text_fields(obj, text_list=None) -> List[str]:
    """Recursively extract all #text fields from the JSON structure."""
    if text_list is None:
        text_list = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "#text" and isinstance(value, str) and value.strip():
                text_list.append(value.strip())
            else:
                extract_all_text_fields(value, text_list)
    elif isinstance(obj, list):
        for item in obj:
            extract_all_text_fields(item, text_list)

    return text_list


def extract_text_from_sentence(sentence_obj) -> str:
    """Extract text from Sentence object in various formats."""
    if isinstance(sentence_obj, dict):
        if "#text" in sentence_obj:
            return sentence_obj["#text"] or ""
        elif "Sentence" in sentence_obj:
            return extract_text_from_sentence(sentence_obj["Sentence"])
        else:
            # Handle different possible structures
            for key, value in sentence_obj.items():
                if isinstance(value, str):
                    return value
                elif isinstance(value, (dict, list)):
                    result = extract_text_from_sentence(value)
                    if result:
                        return result
    elif isinstance(sentence_obj, list):
        texts = []
        for item in sentence_obj:
            text = extract_text_from_sentence(item)
            if text:
                texts.append(text)
        return " ".join(texts)
    elif isinstance(sentence_obj, str):
        return sentence_obj
    return ""


def extract_table_content(table_obj) -> str:
    """Convert table structure to markdown format."""
    if not table_obj:
        return ""

    markdown_table = []

    # Handle both single table and list of tables
    if isinstance(table_obj, list):
        tables = table_obj
    else:
        # If it's a single table object, put it in a list
        tables = [table_obj]

    for table_entry in tables:
        if isinstance(table_entry, dict) and "Table" in table_entry:
            actual_table = table_entry["Table"]
        else:
            actual_table = table_entry

        if "TableRow" in actual_table:
            rows = actual_table["TableRow"]
        else:
            # If it's a single row instead of a list
            rows = (
                [actual_table] if not isinstance(actual_table, list) else actual_table
            )

        if isinstance(rows, dict):
            rows = [rows]
        for row in rows:
            if "TableColumn" in row:
                columns = row["TableColumn"]
                row_texts = []

                # Handle column that might be a single dict or a list of dicts
                if isinstance(columns, list):
                    for col in columns:
                        cell_text = extract_text_from_sentence(col)
                        if cell_text:
                            row_texts.append(cell_text)
                else:
                    # Single column case
                    cell_text = extract_text_from_sentence(columns)
                    if cell_text:
                        row_texts.append(cell_text)

                if row_texts:  # Only add non-empty rows
                    markdown_table.append("| " + " | ".join(row_texts) + " |")

    return "\n".join(markdown_table)


def process_paragraph_content(paragraph_obj) -> str:
    """Process paragraph content recursively."""
    content_parts = []

    if isinstance(paragraph_obj, dict):
        # Check for direct text
        if "ParagraphSentence" in paragraph_obj:
            text = extract_text_from_sentence(paragraph_obj["ParagraphSentence"])
            if text:
                content_parts.append(text)

        # Check for lists
        if "List" in paragraph_obj:
            list_obj = paragraph_obj["List"]
            # Handle both single list item and list of items
            if isinstance(list_obj, dict):
                # Single list item
                if "ListSentence" in list_obj:
                    list_text = extract_text_from_sentence(list_obj["ListSentence"])
                    if list_text:
                        content_parts.append(f"- {list_text}")
            elif isinstance(list_obj, list):
                # Multiple list items
                for list_item in list_obj:
                    if isinstance(list_item, dict) and "ListSentence" in list_item:
                        list_text = extract_text_from_sentence(
                            list_item["ListSentence"]
                        )
                        if list_text:
                            content_parts.append(f"- {list_text}")
            else:
                # Direct handling if ListSentence is directly in the list object
                list_text = extract_text_from_sentence(list_obj)
                if list_text:
                    content_parts.append(f"- {list_text}")

        # Check for tables - now handling both single table struct and list of table structs
        if "TableStruct" in paragraph_obj:
            table_struct = paragraph_obj["TableStruct"]
            if isinstance(table_struct, list):
                # Multiple table structures
                for table_entry in table_struct:
                    table_content = extract_table_content(table_entry)
                    if table_content:
                        content_parts.append(table_content)
            else:
                # Single table structure
                table_content = extract_table_content(table_struct)
                if table_content:
                    content_parts.append(table_content)

        # Recursively check other fields
        for key, value in paragraph_obj.items():
            if key not in [
                "ParagraphSentence",
                "List",
                "TableStruct",
                "ParagraphNum",
                "@Hide",
                "@Num",
                "@OldStyle",
                "@OldNum",
            ]:
                if isinstance(value, (dict, list)):
                    sub_content = process_paragraph_content(value)
                    if sub_content:
                        content_parts.append(sub_content)

    elif isinstance(paragraph_obj, list):
        for item in paragraph_obj:
            sub_content = process_paragraph_content(item)
            if sub_content:
                content_parts.append(sub_content)

    return " ".join(content_parts)


def process_article(article_obj) -> str:
    """Process an article and its paragraphs."""
    article_parts = []

    # Always include the article title
    if "ArticleTitle" in article_obj:
        article_parts.append(f"## {article_obj['ArticleTitle']}")

    if "Paragraph" in article_obj:
        paragraphs = article_obj["Paragraph"]
        if isinstance(paragraphs, list):
            for para in paragraphs:
                content = process_paragraph_content(para)
                if content:
                    article_parts.append(content)
        else:
            content = process_paragraph_content(paragraphs)
            if content:
                article_parts.append(content)

    # Handle any additional content directly in the article
    for key, value in article_obj.items():
        if key not in ["ArticleTitle", "Paragraph", "@Delete", "@Hide", "@Num"]:
            if isinstance(value, (dict, list)):
                extra_content = process_paragraph_content(value)
                if extra_content:
                    article_parts.append(extra_content)

    return "\n\n".join(article_parts)


def extract_title(law_data: Dict[str, Any]) -> str:
    """Extract and combine title information."""
    law_body = law_data.get("LawBody", {})
    law_title = law_body.get("LawTitle", {})

    # Get the main title
    main_title = law_title.get("#text", "")

    # Get abbreviation if available
    abbrev = law_title.get("@Abbrev", "")

    # Combine them if both exist
    if abbrev and abbrev != main_title:
        full_title = f"{main_title} ({abbrev})" if abbrev else main_title
    else:
        full_title = main_title

    # Add law number info
    law_num = law_data.get("LawNum", "")
    if law_num and law_num not in full_title:
        full_title = f"{law_num}: {full_title}"

    return full_title.strip()


def process_supplementary_provision(prov, prov_idx, main_title) -> List[Dict[str, Any]]:
    """Process a single supplementary provision and return list of entries."""
    entries = []
    
    # Get the label for the provision
    prov_label = prov.get("SupplProvisionLabel", f"Supplementary Provision {prov_idx+1}")
    
    # Get amendment law number if available
    amend_law_num = prov.get("@AmendLawNum", "")
    
    # Create a base title with more context
    if amend_law_num:
        prov_title = f"{main_title} - {prov_label} ({amend_law_num})"
    else:
        prov_title = f"{main_title} - {prov_label}"
    
    # Process content differently based on structure
    prov_content = ""
    
    # Check if the provision contains articles
    if "Article" in prov:
        articles = prov["Article"]
        if isinstance(articles, list):
            for article_idx, article in enumerate(articles):
                article_content = process_article(article)
                if article_content.strip():
                    article_title = f"{prov_title} - {article.get('ArticleTitle', f'Article {article_idx+1}')}"
                    entry = {
                        "title": article_title,
                        "text": article_content,
                        "idx": 0  # Will be updated later
                    }
                    entries.append(entry)
        else:
            # Single article case
            article_content = process_article(articles)
            if article_content.strip():
                article_title = f"{prov_title} - {articles.get('ArticleTitle', 'Article')}"
                entry = {
                    "title": article_title,
                    "text": article_content,
                    "idx": 0
                }
                entries.append(entry)
    
    # If no articles were found in the provision, process paragraphs
    if not entries:
        if "Paragraph" in prov:
            paragraphs = prov["Paragraph"]
            if isinstance(paragraphs, list):
                for para_idx, para in enumerate(paragraphs):
                    content = process_paragraph_content(para)
                    if content.strip():
                        # Include paragraph number in title if available
                        para_num = para.get("ParagraphNum", para_idx + 1)
                        para_title = f"{prov_title} - Paragraph {para_num}"
                        entry = {
                            "title": para_title,
                            "text": content,
                            "idx": 0
                        }
                        entries.append(entry)
            else:
                content = process_paragraph_content(paragraphs)
                if content.strip():
                    para_title = f"{prov_title} - Paragraph 1"
                    entry = {
                        "title": para_title,
                        "text": content,
                        "idx": 0
                    }
                    entries.append(entry)
    
    # If still no entries, create a general entry for the provision
    if not entries:
        # Extract all text content as fallback
        all_text_fields = extract_all_text_fields(prov)
        prov_content = "\n".join(all_text_fields)
        if prov_content.strip():
            entry = {
                "title": prov_title,
                "text": prov_content,
                "idx": 0
            }
            entries.append(entry)

    return entries


def transform_law_json_to_articles(file_path: str) -> List[Dict[str, Any]]:
    """Transform a single law JSON file to multiple corpus entries, one per article."""
    with open(file_path, "r", encoding="utf-8") as f:
        law_data = json.load(f)

    law = law_data.get("Law", {})
    
    # Extract main title
    main_title = extract_title(law)
    
    corpus_entries = []
    
    # Process main provision articles
    if "MainProvision" in law.get("LawBody", {}):
        main_prov = law["LawBody"]["MainProvision"]
        if "Article" in main_prov:
            articles = main_prov["Article"]
            
            if isinstance(articles, list):
                for idx, article in enumerate(articles):
                    article_content = process_article(article)
                    if article_content.strip():  # Only add if there's content
                        article_title = f"{main_title} - {article.get('ArticleTitle', f'Article {idx+1}')}"
                        entry = {
                            "title": article_title,
                            "text": article_content,
                            "idx": len(corpus_entries)  # Will be updated when combining
                        }
                        corpus_entries.append(entry)
            else:
                # Single article case
                article_content = process_article(articles)
                if article_content.strip():
                    article_title = f"{main_title} - {articles.get('ArticleTitle', 'Article')}"
                    entry = {
                        "title": article_title,
                        "text": article_content,
                        "idx": len(corpus_entries)
                    }
                    corpus_entries.append(entry)
    
    # Process supplementary provisions (these may also contain articles)
    if "SupplProvision" in law.get("LawBody", {}):
        suppl_prov = law["LawBody"]["SupplProvision"]
        provisions = suppl_prov if isinstance(suppl_prov, list) else [suppl_prov]
        
        for prov_idx, prov in enumerate(provisions):
            prov_entries = process_supplementary_provision(prov, prov_idx, main_title)
            for entry in prov_entries:
                entry["idx"] = len(corpus_entries)
                corpus_entries.append(entry)

    # If no articles were found, create a single entry with all content
    if not corpus_entries:
        # Extract ALL #text fields from the entire JSON structure
        all_text_fields = extract_all_text_fields(law_data)
        full_text = "\n".join(all_text_fields)
        
        if not full_text:
            full_text = (
                f"Law: {law.get('LawNum', '')}\n"
                + f"Era: {law.get('@Era', '')}, "
                + f"Year: {law.get('@Year', '')}, "
                + f"Number: {law.get('@Num', '')}"
            )
        
        entry = {
            "title": main_title,
            "text": full_text,
            "idx": 0
        }
        corpus_entries.append(entry)

    return corpus_entries


def process_directory(input_dir: Path, output_file: Path):
    """Process all JSON files in directory and create corpus file."""
    corpus_list = []
    idx_counter = 0

    # Get all JSON files in directory
    json_files = [f for f in os.listdir(input_dir) if f.endswith(".json")]

    for filename in json_files:
        file_path = os.path.join(input_dir, filename)
        try:
            entries = transform_law_json_to_articles(file_path)
            # Update the idx for each entry to be globally unique
            for entry in entries:
                entry["idx"] = idx_counter
                idx_counter += 1
                corpus_list.append(entry)
            print(f"Processed: {filename} -> {len(entries)} entries")
        except Exception as e:
            print_exc()
            raise e
            print(f"Error processing {filename}: {str(e)}")

    # Write to output file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(corpus_list, f, ensure_ascii=False, indent=2)

    print(f"Created corpus with {len(corpus_list)} entries in {output_file}")


# Example usage
if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent
    input_directory = (
        ROOT / "data/json_documents"  # Adjust this path to your JSON files location
    )
    output_file = ROOT / "_corpus.json"

    process_directory(input_directory, output_file)