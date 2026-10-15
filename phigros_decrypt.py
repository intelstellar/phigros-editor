# -*- coding: utf-8 -*-
"""
Phigros Save Editor
"""
import sys
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# Import decryption/encryption module from the same directory
sys.path.insert(0, str(Path(__file__).parent))
from phigros_decrypt import (
    load_tables, PhigrosCipher, process_save, save_to_xml,
)


def find_cs_path():
    here = Path(__file__).parent
    candidates = [
        here / "LocalSave_reference.cs",
        here.parent / "LocalSave_reference.cs",
    ]
    for p in candidates:
        if p.exists():
            return p
    return here / "LocalSave_reference.cs"


class PhigrosEditor:
    def __init__(self, root):
        self.root = root
        root.title("Phigros Save Editor by FuwaMintNEKO (Batch Edit Enabled)")
        root.geometry("1100x720")
        root.minsize(900, 560)

        # Data
        self.cipher = None
        self.entries = []
        self.current_xml_path = None
        self.tree_to_index = {}
        self.current_selections = []  # List of currently selected entries indices

        # Initialize cipher first
        try:
            cs_path = find_cs_path()
            tables = load_tables(cs_path)
            self.cipher = PhigrosCipher(tables)
        except Exception as e:
            messagebox.showerror(
                "Failed to Load Encryption Tables",
                f"Cannot load LocalSave_reference.cs:\n{e}\n\n"
                "Please ensure this file is in the same directory as this program."
            )
            root.after(100, root.destroy)
            return

        # Build UI
        self._build_ui()
        self._update_status("Ready. Please click [Open Save] to select a playerprefs.xml file.")

    # ---------------- UI Construction ----------------
    def _build_ui(self):
        # Top toolbar
        top = ttk.Frame(self.root, padding=(8, 6))
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(top, text="Open Save", command=self.open_file).pack(side=tk.LEFT)
        ttk.Button(top, text="Save (Encrypt & Write)", command=self.save_file).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(top, text="Save As…", command=self.save_as_file).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(top, text="Reload", command=self.reload_file).pack(side=tk.LEFT, padx=(6, 0))

        self.file_label = ttk.Label(top, text="(No file opened)", foreground="#666")
        self.file_label.pack(side=tk.LEFT, padx=(14, 0))

        # Search bar
        search_frame = ttk.Frame(self.root, padding=(8, 4))
        search_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_change)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6))

        ttk.Label(search_frame, text="Scope:").pack(side=tk.LEFT)
        self.search_scope = ttk.Combobox(
            search_frame, state="readonly", width=10,
            values=["All", "Key", "Value"],
        )
        self.search_scope.set("All")
        self.search_scope.bind("<<ComboboxSelected>>", lambda e: self._on_search_change())
        self.search_scope.pack(side=tk.LEFT)

        ttk.Button(search_frame, text="Select All Shown", command=self.select_all_shown).pack(side=tk.LEFT, padx=(8, 0))

        self.match_count_label = ttk.Label(search_frame, text="", foreground="#666")
        self.match_count_label.pack(side=tk.LEFT, padx=(10, 0))

        # Middle list (Treeview) - selectmode="extended" allows Shift/Ctrl multi-select
        list_frame = ttk.Frame(self.root)
        list_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))

        columns = ("idx", "key", "value", "type", "status")
        self.tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", selectmode="extended"
        )
        self.tree.heading("idx", text="#")
        self.tree.heading("key", text="Key")
        self.tree.heading("value", text="Value")
        self.tree.heading("type", text="Type")
        self.tree.heading("status", text="Status")
        self.tree.column("idx", width=50, stretch=False, anchor="e")
        self.tree.column("key", width=320, stretch=True)
        self.tree.column("value", width=420, stretch=True)
        self.tree.column("type", width=60, stretch=False, anchor="center")
        self.tree.column("status", width=70, stretch=False, anchor="center")

        # Scrollbars
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        # Highlight modified entries with yellow background
        self.tree.tag_configure("modified", background="#fff3b0")
        self.tree.tag_configure("plain", foreground="#888")
        self.tree.tag_configure("error", foreground="#c0392b")

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Control-a>", lambda e: self.select_all_shown())
        self.tree.bind("<Control-A>", lambda e: self.select_all_shown())

        # Bottom edit area
        edit_frame = ttk.LabelFrame(self.root, text="Edit Selected Entry's Value (Supports Multi-Select)", padding=(8, 6))
        edit_frame.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(0, 4))
        edit_frame.columnconfigure(1, weight=1)

        ttk.Label(edit_frame, text="Key:").grid(row=0, column=0, sticky="nw", pady=(0, 4))
        self.key_display = tk.Text(edit_frame, height=2, wrap="word",
                                   state="disabled", background="#f4f4f4")
        self.key_display.grid(row=0, column=1, sticky="ew", pady=(0, 4))

        ttk.Label(edit_frame, text="Value:").grid(row=1, column=0, sticky="nw")
        self.value_edit = tk.Text(edit_frame, height=6, wrap="none")
        self.value_edit.grid(row=1, column=1, sticky="ew")
        val_vsb = ttk.Scrollbar(edit_frame, orient="vertical", command=self.value_edit.yview)
        val_vsb.grid(row=1, column=2, sticky="ns")
        self.value_edit.configure(yscrollcommand=val_vsb.set)

        btn_row = ttk.Frame(edit_frame)
        btn_row.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        ttk.Button(btn_row, text="Apply Changes to List", command=self.apply_edit).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Discard Changes (Restore Original)", command=self.discard_edit).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(btn_row, text="Format JSON", command=self.format_json).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(btn_row, text="Minify JSON", command=self.compress_json).pack(side=tk.LEFT, padx=(6, 0))
        self.edit_hint = ttk.Label(btn_row, text="", foreground="#666")
        self.edit_hint.pack(side=tk.LEFT, padx=(14, 0))

        # Bottom status bar
        status_frame = ttk.Frame(self.root, padding=(8, 4))
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var = tk.StringVar()
        ttk.Label(status_frame, textvariable=self.status_var, foreground="#333").pack(side=tk.LEFT)
        self.modified_count_var = tk.StringVar(value="Modified: 0")
        ttk.Label(status_frame, textvariable=self.modified_count_var, foreground="#c0392b").pack(side=tk.RIGHT)

    # ---------------- Toolbar Actions ----------------
    def open_file(self):
        path = filedialog.askopenfilename(
            title="Select Phigros Save File",
            filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")],
            initialdir=str(Path.home()),
        )
        if not path:
            return
        self._load_file(path)

    def reload_file(self):
        if self.current_xml_path:
            self._load_file(self.current_xml_path)

    def _load_file(self, path):
        try:
            entries = process_save(path, self.cipher)
        except Exception as e:
            messagebox.showerror("Decryption Failed", f"Failed to read or decrypt file:\n{e}")
            return
        self.entries = entries
        self.current_xml_path = path
        self.file_label.config(text=str(path))
        self._populate_tree(entries)
        total = len(entries)
        enc = sum(1 for e in entries if e["type"] == "string" and e.get("encrypted"))
        plain_str = sum(1 for e in entries if e["type"] == "string" and not e.get("encrypted"))
        non_str = sum(1 for e in entries if e["type"] != "string")
        self._update_status(f"Loaded {total} entries; Encrypted: {enc}; Plaintext: {plain_str}; Non-string: {non_str}.")
        self._update_modified_count()

    def save_file(self):
        if not self.current_xml_path:
            messagebox.showwarning("Not Saved", "Please open a save file first.")
            return
        self._do_save(self.current_xml_path)

    def save_as_file(self):
        if not self.entries:
            messagebox.showwarning("Not Saved", "Please open a save file first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension=".xml",
            filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")],
            initialfile="playerprefs_new.xml",
        )
        if not path:
            return
        try:
            import shutil
            shutil.copy2(self.current_xml_path, path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy original file:\n{e}")
            return
        self._do_save(path, backup=False)

    def _do_save(self, path, backup=True):
        modified = sum(1 for e in self.entries
                       if not e.get("value_error")
                       and e["value"] != e.get("original_value"))
        if modified == 0:
            if not messagebox.askyesno("Notice", "No entries were modified. Write back to file anyway?"):
                return
        try:
            n = save_to_xml(path, self.cipher, self.entries, backup=backup)
        except Exception as e:
            messagebox.showerror("Save Failed", f"Encryption or write-back failed:\n{e}")
            return
        for e in self.entries:
            e["original_value"] = e["value"]
        self._populate_tree(self._current_filter_entries())
        bak_msg = f"; Backup: {path}.bak" if backup else ""
        self._update_status(f"Saved to {path}; Updated {n} entries{bak_msg}.")
        self._update_modified_count()
        messagebox.showinfo("Save Successful", f"Updated {n} entries and wrote to:\n{path}")

    # ---------------- List Population & Search ----------------
    def _populate_tree(self, entries_subset=None):
        self.tree.delete(*self.tree.get_children())
        self.tree_to_index.clear()
        if entries_subset is None:
            for i, e in enumerate(self.entries):
                self._insert_entry(i, e)
        else:
            subset_ids = {id(e) for e in entries_subset}
            for i, e in enumerate(self.entries):
                if id(e) in subset_ids:
                    self._insert_entry(i, e)

    def _entry_status_and_tags(self, e):
        modified = (not e.get("value_error")
                    and e["value"] != e.get("original_value"))
        if e.get("value_error"):
            status = "Error"
        elif modified:
            status = "Modified"
        elif e["type"] != "string":
            status = e["type"]
        elif not e.get("encrypted", True):
            status = "Plaintext"
        else:
            status = "—"

        tags = []
        if modified:
            tags.append("modified")
        if e["type"] != "string" or not e.get("encrypted", True):
            tags.append("plain")
        if e.get("value_error"):
            tags.append("error")
        return status, tags

    def _insert_entry(self, idx, e):
        key_text = e.get("key") or f"[Undecrypted] {e['raw_key'][:40]}"
        val_text = e.get("value")
        if val_text is None:
            val_text = f"[Error] {e.get('value_error') or ''}"
        key_disp = key_text if len(key_text) <= 200 else key_text[:200] + "…"
        val_disp = val_text if len(val_text) <= 500 else val_text[:500] + "…"

        status, tags = self._entry_status_and_tags(e)

        item = self.tree.insert(
            "", "end",
            values=(idx + 1, key_disp, val_disp, e["type"], status),
            tags=tags,
        )
        self.tree_to_index[item] = idx

    def _current_filter_entries(self):
        q = self.search_var.get().strip().lower()
        scope = self.search_scope.get()
        if not q:
            return list(self.entries)
        result = []
        for e in self.entries:
            k = (e.get("key") or "").lower()
            v = (e.get("value") or "").lower()
            if scope == "Key":
                if q in k:
                    result.append(e)
            elif scope == "Value":
                if q in v:
                    result.append(e)
            else:
                if q in k or q in v:
                    result.append(e)
        return result

    def _on_search_change(self, *args):
        self._populate_tree(self._current_filter_entries())
        n = len(self.tree.get_children())
        self.match_count_label.config(text=f"Matched: {n}")

    def select_all_shown(self):
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children)
        return "break"

    # ---------------- Selection & Editing ----------------
    def _on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            self.current_selections = []
            return
        indices = [self.tree_to_index[item] for item in sel if item in self.tree_to_index]
        if not indices:
            self.current_selections = []
            return
        self.current_selections = indices

        if len(indices) == 1:
            idx = indices[0]
            e = self.entries[idx]

            # Display Key
            self.key_display.config(state="normal")
            self.key_display.delete("1.0", "end")
            key_text = e.get("key") or f"[Undecrypted] {e['raw_key']}"
            self.key_display.insert("1.0", key_text)
            self.key_display.config(state="disabled")

            # Display Value
            self.value_edit.delete("1.0", "end")
            val = e.get("value")
            if val is None:
                val = f"[Error] {e.get('value_error') or ''}"
            self.value_edit.insert("1.0", val)

            # Hints
            if e.get("value_error"):
                self.edit_hint.config(text=f"Cannot decrypt this entry: {e['value_error']}, not editable.")
            elif e["type"] == "string" and not e.get("encrypted", True):
                self.edit_hint.config(text="Plaintext string, Value is editable. Click [Apply Changes to List] when done.")
            elif e["type"] != "string":
                self.edit_hint.config(text=f"{e['type']} type, Value is editable. Click [Apply Changes to List] when done.")
            else:
                self.edit_hint.config(text="Value is editable. Click [Apply Changes to List] when done.")
        else:
            # Multiple items selected
            first_e = self.entries[indices[0]]
            self.key_display.config(state="normal")
            self.key_display.delete("1.0", "end")
            sample_keys = ", ".join((self.entries[i].get("key") or "")[:30] for i in indices[:3])
            more = "..." if len(indices) > 3 else ""
            self.key_display.insert("1.0", f"[{len(indices)} entries selected] ({sample_keys}{more})")
            self.key_display.config(state="disabled")

            # Show first item's value if all share the same value, or just show the first one as template
            self.value_edit.delete("1.0", "end")
            val = first_e.get("value") or ""
            self.value_edit.insert("1.0", val)

            self.edit_hint.config(
                text=f"Batch Mode: {len(indices)} entries selected. Editing Value and clicking [Apply] will update ALL selected entries!"
            )

    def _on_tree_double_click(self, event):
        if not self.current_selections:
            return
        self.format_json()

    def apply_edit(self):
        if not self.current_selections:
            messagebox.showinfo("Notice", "Please select at least one record from the list first.")
            return

        new_val = self.value_edit.get("1.0", "end-1c")

        # Validate if any selected item is int
        has_int = any(self.entries[idx]["type"] == "int" for idx in self.current_selections)
        if has_int:
            try:
                int(new_val.strip())
            except ValueError:
                if not messagebox.askyesno(
                    "Type Warning",
                    f"One or more selected entries are of type 'int', but the input \"{new_val.strip()}\" is not a valid integer.\nApply anyway?"
                ):
                    return

        updated = 0
        skipped = 0
        for idx in self.current_selections:
            e = self.entries[idx]
            if e.get("value_error"):
                skipped += 1
                continue
            e["value"] = new_val
            self._update_tree_row(idx)
            updated += 1

        self._update_modified_count()
        skip_msg = f" ({skipped} undecryptable skipped)" if skipped else ""
        self.edit_hint.config(text=f"Applied to {updated} entries{skip_msg}. Click [Save] to write back to file.")

    def discard_edit(self):
        if not self.current_selections:
            return
        for idx in self.current_selections:
            e = self.entries[idx]
            e["value"] = e.get("original_value")
            self._update_tree_row(idx)

        first_e = self.entries[self.current_selections[0]]
        self.value_edit.delete("1.0", "end")
        self.value_edit.insert("1.0", first_e["value"] or "")
        self._update_modified_count()
        self.edit_hint.config(text=f"Restored {len(self.current_selections)} selected entries to original value.")

    def format_json(self):
        if not self.current_selections:
            return
        cur = self.value_edit.get("1.0", "end-1c").strip()
        if not cur:
            return
        try:
            obj = json.loads(cur)
            pretty = json.dumps(obj, ensure_ascii=False, indent=2)
            self.value_edit.delete("1.0", "end")
            self.value_edit.insert("1.0", pretty)
            self.edit_hint.config(text="JSON formatted (not yet applied, click [Apply Changes to List]).")
        except json.JSONDecodeError as ex:
            self.edit_hint.config(text=f"Invalid JSON: {ex}")

    def compress_json(self):
        if not self.current_selections:
            return
        cur = self.value_edit.get("1.0", "end-1c").strip()
        if not cur:
            return
        try:
            obj = json.loads(cur)
            compact = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            self.value_edit.delete("1.0", "end")
            self.value_edit.insert("1.0", compact)
            self.edit_hint.config(text="JSON minified (not yet applied, click [Apply Changes to List]).")
        except json.JSONDecodeError as ex:
            self.edit_hint.config(text=f"Invalid JSON: {ex}")

    def _update_tree_row(self, idx):
        for item, i in self.tree_to_index.items():
            if i == idx:
                e = self.entries[idx]
                key_text = e.get("key") or f"[Undecrypted] {e['raw_key'][:40]}"
                val_text = e.get("value") or ""
                key_disp = key_text if len(key_text) <= 200 else key_text[:200] + "…"
                val_disp = val_text if len(val_text) <= 500 else val_text[:500] + "…"
                status, tags = self._entry_status_and_tags(e)
                self.tree.item(item, values=(idx + 1, key_disp, val_disp, e["type"], status), tags=tags)
                break

    # ---------------- Status Bar ----------------
    def _update_status(self, msg):
        self.status_var.set(msg)

    def _update_modified_count(self):
        n = sum(1 for e in self.entries
                if not e.get("value_error")
                and e["value"] != e.get("original_value"))
        self.modified_count_var.set(f"Modified: {n}")


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass
    app = PhigrosEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
