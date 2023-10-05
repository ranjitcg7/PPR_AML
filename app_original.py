import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional, Set
import streamlit as st
from pydantic import BaseModel, Field
from pydantic.color import Color
from PIL import Image
import json

from st_cytoscape import cytoscape
from streamlit_antd_components import antd_menu, MenuItem, MenuDivider, antd_tree, TreeItem
from streamlit_agraph import agraph, Node, Edge, Config
from streamlit_agraph.config import Config, ConfigBuilder
import subprocess
import streamlit_pydantic as sp
from st_ant_tree import st_ant_tree

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

from c2_IH_extractor import GetIH

from c1_generates_PPR_IH import GenerateTrees
# from c1_generates_PPR_IH import product_tree, process_tree, resource_tree
# from c2_generates_connected_PPRs import GetConnections
# from c2_generates_connected_PPRs import GetConnections
#from c3_generates_views import Generate_views
# from c3_generates_views import Generate_views
#from c4_view_merger import JSONMerger
from c3_views_generator import Generate_Views

##aml-json converter
from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.parsers import XmlParser
from aml_base import Caexfile
from Py4AML_JSON_main.R_aml_json_converter import convert_aml_to_json

from xsdata.formats.dataclass.parsers import JsonParser
from xsdata.formats.dataclass.serializers import XmlSerializer 
from xsdata.formats.dataclass.context import XmlContext

### firestore database 
# Use a service account
cred = credentials.Certificate('DBkey.json')
  
# check if the app is already initialized to avoid ValueError: The default Firebase app already exists.
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# set page icon
icon=Image.open('Logo_4.png')
st.set_page_config(page_title="PPR-AML", page_icon=icon, layout="wide")

# st.image(icon, width = 150, ) # create a column and place it
st.title("PPR - AML")



with st.sidebar:
    st.image(icon, width = 150, ) # create a column and place it
    st.title("PPR - AML")
    st.subheader("Upload your files here")

# Upload different views/ files
    uploaded_files = st.file_uploader("Upload AML file", accept_multiple_files=True)
    uploaded_file_names = []
    for uploaded_file in uploaded_files:
        file_extension = uploaded_file.name.split('.')[-1]  # Get the file extension

        if file_extension == 'aml':
            bytes_data = uploaded_file.getvalue()

            context = XmlContext()
            parser = XmlParser(context=context)
            aml_object: Caexfile = parser.from_string(str(bytes_data, 'utf-8'), Caexfile)

            st.session_state["aml_object"] = aml_object
            st.session_state["file_name"] = uploaded_file.name[:-4]
            st.session_state["uploaded_file_size"] = uploaded_file.size / 1000

            indent = True
            indent_value = 4

            cleaned_json = convert_aml_to_json(st.session_state["aml_object"], indent_value)
            

            # Add the file name to the list
            uploaded_file_names.append(uploaded_file.name)

            # convert string (in json format) to python dictionary
            data = json.loads(cleaned_json)
            doc_ref = db.collection('uploaded_views').document(uploaded_file.name)
            doc_ref.set(data)

        elif file_extension == 'json':
            st.write(f'The file {uploaded_file.name} is in JSON format.')
            file_bytes = uploaded_file.read()  # this is bytes

            # Add the file name to the list
            uploaded_file_names.append(uploaded_file.name)

            # convert bytes to string
            file_str = file_bytes.decode('utf-8')
            
            # convert string (in json format) to python dictionary
            data = json.loads(file_str)
            doc_ref = db.collection('uploaded_views').document(uploaded_file.name)
            doc_ref.set(data)

        else:
            st.write(f'The file {uploaded_file.name} has an unrecognized format: .{file_extension}')

# Integrating uploaded  files
    integrate_button = st.button('Integrate files', type="primary", key="integrate_button")

## Can add only one final .aml  file  right now. Later extend to merge multiple files
    if integrate_button:

        # Use a service account
        cred = credentials.Certificate('DBkey.json')

        # check if the app is already initialized to avoid ValueError: The default Firebase app already exists.
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        # Fetch all documents in the collection
        docs = db.collection('uploaded_views').stream()

        # Convert to a list
        docs_list = list(docs)

        # Initialize merged_dict with the first document
        merged_dict = docs_list[0].to_dict()

        if len(docs_list) == 1:
            # Save the result back to Firestore
            db.collection('payload').document('payload_aml-json_merged_views').set(merged_dict)
            st.success("Successfully uploaded AML file")

        else:



            #### Here i want to add that Integration feature






            # Save the result back to Firestore
            db.collection('payload').document('payload_aml-json_merged_views').set(merged_dict)
            st.success("Successfully Integrated")



## extract IHs from the Payload
    if integrate_button:
        instances = GetIH()
        instances.extract_IH()






# Downloading integrated files
    # Create XML context and JSON parser
    context = XmlContext()
    json_parser = JsonParser(context=context)

    # Fetch the integrated file from Firestore
    integrated_file_ref = db.collection('payload').document('payload_aml-json_merged_views')

    # Get the document snapshot of the integrated file
    integrated_file_snapshot = integrated_file_ref.get()

    if integrated_file_snapshot.exists:
        # Convert the DocumentSnapshot to a dictionary
        data = integrated_file_snapshot.to_dict()

        # bind the data to the AML data model using the json parser
        aml_object: Caexfile = json_parser.bind_dataclass(data, Caexfile)

        # serialize the AML object to xml string
        xml_string = XmlSerializer(context=context).render(aml_object)

        #st.write(f'The integrated file was in JSON format and has been converted to AML.')
        st.download_button(
            label="Download converted AML file",
            data=xml_string.encode('utf-8'),  # encode to bytes
            file_name="integrated_file.aml",
            mime='application/xml'
        )
    else:
        st.write("No integrated file found in Firestore.")


# Deleting old  files
    if st.button('Delete old files', key="delete-sidebar", ):
        # Fetch all documents in the collection
        old_docs = db.collection('uploaded_views').stream()
        for doc in old_docs:
            # Delete each document
            db.collection('uploaded_views').document(doc.id).delete()
            db.collection('Extracted_views').document(doc.id).delete()
            db.collection('utils').document(doc.id).delete()

        st.success('Successfully deleted old files')



tab1, tab2 = st.tabs(["Assets", "Attributes"])


with tab1:
    # st.header("Instance Hierarchy")

    # 3 columns 
    col_IH, col_connections, col_views = st.columns(3)

    ### Column 1
    with col_IH:
        st.subheader("Instance Hierarchy")

        # call Class from C1
        generate_trees = GenerateTrees()
        product_children, process_children, resource_children = generate_trees.ppr_tree()

        #### the following method is perfect for converting list to antd tree list structure ####
        def convert_to_antd_tree_item(self_tree_item_list):
            return [TreeItem(item.name, item.id) for item in self_tree_item_list]

        product_children = convert_to_antd_tree_item(product_children)
        process_children = convert_to_antd_tree_item(process_children)
        resource_children = convert_to_antd_tree_item(resource_children)
        #### the above method is perfect for converting list to antd tree list structure ####


        tree_IH = [TreeItem('Products:', '100', children = product_children),
                TreeItem('Process:', '200', children = process_children),
                TreeItem('Resuorce:', '300', children = resource_children)  ]

        instance = antd_tree(
            items=tree_IH,
            checkbox=False,
            show_line=True,
            icon=None,
            expand_all=True,
            selected_keys=[1],
            key=1,
        )   
        data = {'Name': "selected_IH", 'ID': instance[0]}
        db.collection('UserInteraction').document("selected_IH").set(data)
        selected_instance = instance[0]

        

    with col_connections:
        st.subheader("Connections")

        # connections = GetConnections(selected_instance)
        # connected_products, connected_processes, connected_resources = connections.filter_items_by_id()

        # def convert_to_antd_tree_item(self_tree_item_list):
        #     return [TreeItem(item.name, item.id) for item in self_tree_item_list]

        # connected_products = convert_to_antd_tree_item(connected_products)
        # connected_processes = convert_to_antd_tree_item(connected_processes)
        # connected_resources = convert_to_antd_tree_item(connected_resources)

        # tree_list = [TreeItem('Connected Products:', '1', children = connected_products),
        #             TreeItem('Connected Process:', '2', children = connected_processes),
        #             TreeItem('Connected Resource:', '3', children = connected_resources),]

        # instance2 = antd_tree(
        #     items=tree_list,
        #     checkbox=False,
        #     show_line=True,
        #     icon=None,
        #     expand_all=True, 
        #     key= 2    
        # )
        # # st.write(f'The selected item key is **{instance2}**')



    

    with col_views:
        st.subheader("Views")  
 
        # call Class from C3
        views = Generate_Views()
        id_to_search = views.get_IH_id()
        views_list = views.ppr_tree(id_to_search)

        #### the following method is perfect for converting list to antd tree list structure ####
        def convert_to_antd_tree_item(self_tree_item_list):
            return [TreeItem(item.name, item.id) for item in self_tree_item_list]

        views_tree = convert_to_antd_tree_item(views_list)

        #### the above method is perfect for converting list to antd tree list structure ####


        tree_V = [TreeItem('Views:', '100', children = views_tree)]

        view = antd_tree(
            items=tree_V,
            checkbox=False,
            show_line=True,
            icon=None,
            expand_all=True,
            selected_keys=[1],
            key="views_tree",
        )   
        data = {'Name': "selected_View", 'ID': view[0]}
        db.collection('UserInteraction').document("selected_view").set(data)
        selected_view = view[0]
        




with tab2:

    # 2 columns 
    col_views, col_attributes = st.columns([1,6])

    with col_views:
        st.header("Views")

  





    with col_attributes:
        st.header("Attributes")