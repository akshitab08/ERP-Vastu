import os
import frappe
from frappe.integrations.doctype.google_drive.google_drive import get_google_drive_object
from apiclient.http import MediaFileUpload
from frappe.utils import get_bench_path

def organize_employee_documents(doc, method):
    employee_code = doc.name
    google_drive, account = get_google_drive_object()
    # base_drive_folder_id = "18Zy-B00JuscNm_rPWnty9rwtQp8l6h8Y"
    frappe_base_folder = create_folder("employees", "Home")
    frappe_employee_folder = create_folder(employee_code, frappe_base_folder)
    drive_employee_folder = create_drive_folder(employee_code, google_drive)

    for i in doc.get("custom_document_", []):
        if not i.document_type or not i.file:
            frappe.logger().error(f"Skipping file: Missing document_type or file for {i}")
            continue  
        
        frappe_doc_folder = create_folder(i.document_type, frappe_employee_folder)
       
        drive_doc_folder = create_drive_folder(i.document_type, google_drive, drive_employee_folder)

        link_file(i.file, frappe_doc_folder)
  
        file_id = upload_file_to_drive(drive_doc_folder, google_drive, i.file)
        
        if file_id:
            frappe.logger().info(f"Successfully uploaded {i.file} to Google Drive Folder: {i.document_type}")

def create_folder(folder_name, parent_folder):
    folder_exists = frappe.db.exists("File", {"file_name": folder_name, "folder": parent_folder})
    
    if not folder_exists:
        folder = frappe.get_doc({
            "doctype": "File",
            "file_name": folder_name,
            "folder": parent_folder,  
            "is_folder": 1
        })
        folder.insert(ignore_permissions=True)
    
    return f"{parent_folder}/{folder_name}"

def link_file(file_url, target_folder):
    if frappe.db.exists("File", {"file_url": file_url}):
        original_file = frappe.get_doc("File", {"file_url": file_url})
        frappe.get_doc({
            "doctype": "File",
            "file_name": original_file.file_name,
            "file_url": original_file.file_url, 
            "folder": target_folder,
            "is_private": original_file.is_private
        }).insert(ignore_permissions=True)

def create_drive_folder(folder_name, google_drive, parent_folder_id=None):
    try:
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"

        if parent_folder_id:
            query += f" and '{parent_folder_id}' in parents"

        existing_folders = google_drive.files().list(q=query).execute().get("files", [])
        if existing_folders:
            return existing_folders[0]["id"]

        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }

        
        if parent_folder_id:
            folder_metadata["parents"] = [parent_folder_id]

        folder = google_drive.files().create(body=folder_metadata).execute()
        return folder.get("id")
    except Exception as e:
        frappe.logger().error(f"Failed to create folder {folder_name}: {str(e)}")
        return None

#used to upload the file
def upload_file_to_drive(target_drive_folder_id, google_drive, file_url):
    if file_url:
        #print("--------------------")
        file_path = os.path.join(frappe.local.site, file_url.lstrip("/"))
    else:
        frappe.logger().error(f"Invalid file URL: {file_url}")
        return None

    if not os.path.exists(file_path):
        frappe.logger().error(f"File not found: {file_path}")
        return None   
    try:
        file_metadata = {
            "name": os.path.basename(file_path),
            "parents": [target_drive_folder_id]
        }
        media = MediaFileUpload(file_path, resumable=True)
        uploaded_file = google_drive.files().create(body=file_metadata, media_body=media).execute()

        frappe.logger().info(f"Uploaded: {uploaded_file.get('name')} (ID: {uploaded_file.get('id')})")
        return uploaded_file.get("id")
    except Exception as e:
        frappe.logger().error(f"File upload failed for {file_path}: {str(e)}")
        return None
