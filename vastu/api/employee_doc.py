import frappe
import os

def organize_employee_documents(doc, method):
    employee_code = doc.name
    
    # Step 1: Ensure the base folders exist
    base_folder = create_folder("employees", "Home")  
    employee_folder = create_folder(employee_code, base_folder) 

    for i in doc.get("custom_document_", []):
        if not i.document_type or not i.file:
            continue  
      
        doc_folder = create_folder(i.document_type, employee_folder)
        
        link_file(i.file, doc_folder)

def create_folder(folder_name, parent_folder):
    """
    Creates a folder inside the given parent folder in File Manager.
    Returns the folder path.
    """
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
    """
    Creates a new File entry inside the target folder without moving the original file.
    """

    if frappe.db.exists("File", {"file_url": file_url}):
        original_file = frappe.get_doc("File", {"file_url": file_url})
        
        frappe.get_doc({
            "doctype": "File",
            "file_name": original_file.file_name,
            "file_url": original_file.file_url, 
            "folder": target_folder,
            "is_private": original_file.is_private
        }).insert(ignore_permissions=True)
        frappe.delete_doc("File", original_file.name, force=True)
        
