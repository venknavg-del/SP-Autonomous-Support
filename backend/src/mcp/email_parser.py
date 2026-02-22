import os
import email
from email import policy
import base64
from typing import Dict, Any, List
import extract_msg

def parse_email(file_path: str) -> Dict[str, Any]:
    """
    Parses an email file (.eml, .msg, or .txt) and extracts text body and any inline images.
    Returns a dictionary with 'subject', 'body', and 'images' (list of base64 strings).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Email file not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.msg':
        return _parse_msg(file_path)
    elif ext == '.eml':
        return _parse_eml(file_path)
    elif ext == '.txt':
        return _parse_txt(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

def _parse_txt(file_path: str) -> Dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Try to extract subject if it exists in the first line
    lines = content.split('\n')
    subject = "No Subject"
    if len(lines) > 0 and lines[0].lower().startswith("subject:"):
        subject = lines[0].replace("Subject:", "").strip()
        body = "\n".join(lines[1:]).strip()
    else:
        body = content
        
    return {
        "subject": subject,
        "from": "Unknown Sender",
        "body": body,
        "images": []
    }

def _parse_msg(file_path: str) -> Dict[str, Any]:
    msg = extract_msg.Message(file_path)
    
    parsed_data = {
        "subject": msg.subject or "No Subject",
        "from": msg.sender or "Unknown Sender",
        "body": msg.body or "",
        "images": []
    }
    
    # Extract attachments (specifically images)
    for attachment in msg.attachments:
        if isinstance(attachment, extract_msg.attachment.AttachmentBase):
            try:
                data = attachment.data
                filename = attachment.longFilename or attachment.shortFilename or "attachment"
                mime = "image/png" # crude approximation for MSG, we usually just need base64
                
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    base64_img = base64.b64encode(data).decode('utf-8')
                    parsed_data["images"].append({
                        "filename": filename,
                        "mime_type": mime,
                        "base64_data": base64_img
                    })
            except Exception as e:
                print(f"Error parsing .msg attachment {filename}: {e}")
                
    msg.close()
    return parsed_data

def _parse_eml(file_path: str) -> Dict[str, Any]:
    with open(file_path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    parsed_data = {
        "subject": msg.get("subject", "No Subject"),
        "from": msg.get("from", "Unknown Sender"),
        "body": "",
        "images": []
    }

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if content_type == "text/plain" and "attachment" not in content_disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    parsed_data["body"] += payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
            
            elif content_type.startswith("image/"):
                img_data = part.get_payload(decode=True)
                if img_data:
                    base64_img = base64.b64encode(img_data).decode('utf-8')
                    parsed_data["images"].append({
                        "filename": part.get_filename() or "inline_image",
                        "mime_type": content_type,
                        "base64_data": base64_img
                    })
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            parsed_data["body"] = payload.decode(msg.get_content_charset() or 'utf-8', errors='ignore')

    return parsed_data
