# Amz-Image-Tool
Tool to categorise and create zip file for amz images

## Main Scripts

- **main_tester.py**  
	Debug helper to copy images (model/producttype/colour.jpg) into model/producttype/colour/MAIN.jpg.

- **combined_ui.py**  
	Combined workflow UI for colour and order phases.  
	- Colour Phase: Assign colour sequences to images.
	- Order Phase: Reorder images for each product type.

- **amz_rename.py**  
	Renames images for Amazon using a `sku2asin.csv` mapping.  
	Usage:  
	```
	python amz_rename.py <root>
	```

- **colour_sorter.py**  
	Sorts images into subfolders by colour sequence.  
	Function:  
	```
	run_with_map(root, col_map, apply_changes=True)
	```

- **pt_order.py**  
	Renames images by product type (PT) number.  
	Function:  
	```
	run_with_map(root, pt_map, apply_changes=True, ...)
	```

- **ui_utils.py**  
	Shared UI utilities and constants for image sorting and reordering.

- **undo.py**  
	Extracts PTxx or MAIN tags from filenames and supports undoing renames.

