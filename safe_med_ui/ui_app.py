#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
改进的文本脱敏UI应用
支持：
- 多种文件格式（TXT, DOCX, CSV, XLSX, JSON, JSONL）
- 实时预览和统计
- 灵活的脱敏选项配置
- 词典管理和扩展
"""
import threading
import traceback
from pathlib import Path
from tkinter import Tk, ttk, filedialog, messagebox, StringVar, BooleanVar, Text, END, Listbox, MULTIPLE, scrolledtext, Menu
from typing import Dict, List, Any, Optional
import json

from .config_store import ConfigStore
from .io_utils import (
    load_file, suggest_output_path,
    save_text, save_docx, save_df, save_jsonl,
    get_text_columns
)
from .engine import DeidEngine


def _repo_root() -> Path:
    """获取项目根路径"""
    return Path(__file__).resolve().parents[1]


class ModernSafeMedApp(Tk):
    """现代化的SafeMed脱敏工具UI"""
    
    def __init__(self):
        super().__init__()
        self.title("SafeMed 文本脱敏工具 v2.0")
        self.geometry("1200x750")
        
        # 配置样式
        style = ttk.Style()
        style.theme_use('clam')
        
        # 初始化数据
        self.repo_root = _repo_root()
        self.store = ConfigStore(self.repo_root)
        
        self.terms = self.store.load_terms()
        self.settings = self.store.load_settings() or {}
        
        # UI变量
        self.input_path = StringVar(value="")
        self.output_dir = StringVar(value=self.settings.get("output_dir", ""))
        self.replacement_mode = StringVar(value=self.settings.get("replacement_mode", "tag"))
        self.prefer_native = BooleanVar(value=True)
        self.preview_rows = int(self.settings.get("preview_rows", 50))
        
        # 脱敏类别开关
        default_enable = self.settings.get("enable_categories", {})
        self.enable_id = BooleanVar(value=bool(default_enable.get("id_like", True)))
        self.enable_phone = BooleanVar(value=bool(default_enable.get("phone", True)))
        self.enable_email = BooleanVar(value=bool(default_enable.get("email", True)))
        self.enable_date = BooleanVar(value=bool(default_enable.get("date", True)))
        self.enable_age = BooleanVar(value=bool(default_enable.get("age", True)))
        self.enable_hospital = BooleanVar(value=bool(default_enable.get("hospital_dict", True)))
        self.enable_surnames = BooleanVar(value=bool(default_enable.get("surnames", True)))
        self.enable_doctor_title = BooleanVar(value=bool(default_enable.get("doctor_title", True)))
        self.enable_suffixes = BooleanVar(value=bool(default_enable.get("hospital_suffixes", True)))
        self.enable_custom_terms = BooleanVar(value=bool(default_enable.get("custom_terms", True)))
        
        # 数据状态
        self.loaded = None
        self.selected_cols = []
        self.deidentified_text = ""
        self.deidentified_stats = {}
        self.deidentified_df = None
        self.backend_used = ""
        
        self._build_ui()
        
    def _build_ui(self):
        """构建用户界面"""
        # 创建菜单栏
        menubar = Menu(self)
        self.config(menu=menubar)
        
        file_menu = Menu(menubar)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开文件...", command=self.on_choose_file)
        file_menu.add_command(label="选择输出目录...", command=self.on_choose_outdir)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit)
        
        help_menu = Menu(menubar)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
        
        # 创建Notebook
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 标签1: 脱敏运行
        self.tab_run = ttk.Frame(notebook)
        notebook.add(self.tab_run, text="🔐 脱敏运行")
        self._build_run_tab()
        
        # 标签2: 词典管理
        self.tab_dict = ttk.Frame(notebook)
        notebook.add(self.tab_dict, text="📚 词典管理")
        self._build_dict_tab()
        
        # 标签3: 日志
        self.tab_log = ttk.Frame(notebook)
        notebook.add(self.tab_log, text="📋 日志")
        self._build_log_tab()
        
    def _build_run_tab(self):
        """构建脱敏运行标签页"""
        # 主 Panedwindow：左侧控制面板，右侧预览区
        main_pane = ttk.Panedwindow(self.tab_run, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=5, pady=5)
        
        # ========== 左侧控制面板 ==========
        frm_control = ttk.Frame(main_pane)
        
        # --- 文件选择区 ---
        frm_file = ttk.LabelFrame(frm_control, text="文件选择", padding=8)
        frm_file.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(frm_file, text="输入文件：", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky="w", padx=3, pady=3)
        ttk.Entry(frm_file, textvariable=self.input_path, width=30).grid(row=0, column=1, sticky="we", padx=3, pady=3)
        ttk.Button(frm_file, text="选择", command=self.on_choose_file, width=8).grid(row=0, column=2, padx=3, pady=3)
        
        ttk.Label(frm_file, text="输出目录：", font=("Arial", 9, "bold")).grid(row=1, column=0, sticky="w", padx=3, pady=3)
        ttk.Entry(frm_file, textvariable=self.output_dir, width=30).grid(row=1, column=1, sticky="we", padx=3, pady=3)
        ttk.Button(frm_file, text="选择", command=self.on_choose_outdir, width=8).grid(row=1, column=2, padx=3, pady=3)
        
        frm_file.columnconfigure(1, weight=1)
        
        # --- 脱敏选项区 ---
        frm_opts = ttk.LabelFrame(frm_control, text="脱敏选项", padding=8)
        frm_opts.pack(fill="x", padx=5, pady=5)
        
        # 替换模式
        ttk.Label(frm_opts, text="替换模式：", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky="w", padx=3, pady=3)
        ttk.Radiobutton(frm_opts, text="标签", value="tag", variable=self.replacement_mode, width=6).grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(frm_opts, text="掩码", value="mask", variable=self.replacement_mode, width=6).grid(row=0, column=2, sticky="w")
        
        ttk.Checkbutton(frm_opts, text="优先safe_med", variable=self.prefer_native, width=15).grid(row=0, column=3, sticky="w", padx=3)
        
        # 脱敏类别 - 紧凑显示
        ttk.Label(frm_opts, text="脱敏类别：", font=("Arial", 9, "bold")).grid(row=1, column=0, columnspan=4, sticky="w", padx=3, pady=5)
        
        categories = [
            ("身份证", self.enable_id, 2, 0),
            ("手机号", self.enable_phone, 2, 1),
            ("邮箱", self.enable_email, 2, 2),
            ("日期", self.enable_date, 2, 3),
            ("年龄", self.enable_age, 3, 0),
            ("医院", self.enable_hospital, 3, 1),
            ("姓名", self.enable_surnames, 3, 2),
            ("医生", self.enable_doctor_title, 3, 3),
            ("机构", self.enable_suffixes, 4, 0),
            ("词典", self.enable_custom_terms, 4, 1),
        ]
        
        for label, var, row, col in categories:
            ttk.Checkbutton(frm_opts, text=label, variable=var, width=8).grid(row=row, column=col, sticky="w", padx=2, pady=2)
        
        # --- 结构化文件列选择 ---
        frm_cols = ttk.LabelFrame(frm_control, text="数据列选择", padding=8)
        frm_cols.pack(fill="both", expand=True, padx=5, pady=5)
        
        ttk.Label(frm_cols, text="选择脱敏的列：", font=("Arial", 9)).pack(anchor="w", padx=3, pady=2)
        
        scrollbar = ttk.Scrollbar(frm_cols)
        scrollbar.pack(side="right", fill="y")
        
        self.cols_list = Listbox(frm_cols, selectmode=MULTIPLE, height=6, yscrollcommand=scrollbar.set)
        self.cols_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.cols_list.yview)
        
        # --- 操作按钮区 ---
        frm_action = ttk.Frame(frm_control)
        frm_action.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(frm_action, text="📊 预览", command=self.on_preview, width=12).pack(side="left", padx=2)
        ttk.Button(frm_action, text="⚡ 脱敏导出", command=self.on_run, width=12).pack(side="left", padx=2)
        
        # 添加到主 Panedwindow
        main_pane.add(frm_control, weight=0)
        
        # ========== 右侧预览区 ==========
        frm_preview = ttk.LabelFrame(main_pane, text="预览区域（左：原文 | 右：脱敏后）", padding=5)
        
        pane = ttk.Panedwindow(frm_preview, orient="horizontal")
        pane.pack(fill="both", expand=True)
        
        # 左侧：原文本
        frm_left = ttk.Frame(pane)
        ttk.Label(frm_left, text="原文本", font=("Arial", 9, "bold")).pack(anchor="w", padx=3, pady=2)
        self.txt_in = scrolledtext.ScrolledText(frm_left, wrap="word", height=15)
        self.txt_in.pack(fill="both", expand=True)
        pane.add(frm_left, weight=1)
        
        # 右侧：脱敏后
        frm_right = ttk.Frame(pane)
        ttk.Label(frm_right, text="脱敏后文本", font=("Arial", 9, "bold")).pack(anchor="w", padx=3, pady=2)
        self.txt_out = scrolledtext.ScrolledText(frm_right, wrap="word", height=15)
        self.txt_out.pack(fill="both", expand=True)
        
        # 为脱敏后的文本配置高亮标签
        self.txt_out.tag_config("modified", background="#FFFF99", foreground="#000000")  # 黄色背景高亮
        self.txt_out.tag_config("phone", background="#FFB6C1", foreground="#000000")      # 浅红色
        self.txt_out.tag_config("id", background="#87CEEB", foreground="#000000")         # 天蓝色
        self.txt_out.tag_config("name", background="#90EE90", foreground="#000000")       # 浅绿色
        self.txt_out.tag_config("date", background="#FFD700", foreground="#000000")       # 金色
        self.txt_out.tag_config("hospital", background="#FFA500", foreground="#000000")   # 橙色
        
        pane.add(frm_right, weight=1)
        
        # 添加预览区到主 Panedwindow
        main_pane.add(frm_preview, weight=1)
        
        # 进度条 - 放在底部
        self.prog = ttk.Progressbar(self.tab_run, mode="indeterminate")
        self.prog.pack(fill="x", padx=5, pady=2)
        
        # 统计信息标签
        self.stat_label = ttk.Label(self.tab_run, text="", relief="sunken", font=("Arial", 8))
        self.stat_label.pack(fill="x", padx=5, pady=2)
        
    def _build_dict_tab(self):
        """构建词典管理标签页"""
        frm_dict = ttk.Frame(self.tab_dict, padding=10)
        frm_dict.pack(fill="both", expand=True)
        
        # 左侧：类别列表
        frm_left = ttk.LabelFrame(frm_dict, text="词典类别", padding=5)
        frm_left.pack(side="left", fill="both", expand=False, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(frm_left)
        scrollbar.pack(side="right", fill="y")
        
        self.cat_list = Listbox(frm_left, height=25, width=20, yscrollcommand=scrollbar.set)
        self.cat_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.cat_list.yview)
        self.cat_list.bind("<<ListboxSelect>>", lambda e: self.refresh_terms_list())
        
        frm_cat_btn = ttk.Frame(frm_left)
        frm_cat_btn.pack(fill="x", pady=5)
        ttk.Button(frm_cat_btn, text="新增", command=self.on_add_category, width=8).pack(side="left", padx=2)
        ttk.Button(frm_cat_btn, text="删除", command=self.on_del_category, width=8).pack(side="left", padx=2)
        
        # 右侧：词条列表
        frm_right = ttk.LabelFrame(frm_dict, text="词条内容", padding=5)
        frm_right.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        scrollbar2 = ttk.Scrollbar(frm_right)
        scrollbar2.pack(side="right", fill="y")
        
        self.term_list = Listbox(frm_right, height=25, yscrollcommand=scrollbar2.set)
        self.term_list.pack(side="left", fill="both", expand=True)
        scrollbar2.config(command=self.term_list.yview)
        
        frm_term_btn = ttk.Frame(frm_right)
        frm_term_btn.pack(fill="x", pady=5)
        ttk.Button(frm_term_btn, text="添加", command=self.on_add_term, width=8).pack(side="left", padx=2)
        ttk.Button(frm_term_btn, text="删除", command=self.on_del_term, width=8).pack(side="left", padx=2)
        ttk.Button(frm_term_btn, text="导入TXT", command=self.on_import_terms, width=8).pack(side="left", padx=2)
        ttk.Button(frm_term_btn, text="保存", command=self.on_save_terms, width=8).pack(side="right", padx=2)
        
        self.refresh_category_list()
        
    def _build_log_tab(self):
        """构建日志标签页"""
        frm_log = ttk.Frame(self.tab_log, padding=10)
        frm_log.pack(fill="both", expand=True)
        
        ttk.Label(frm_log, text="运行日志：", font=("Arial", 10, "bold")).pack(anchor="w", padx=5, pady=5)
        
        self.log = scrolledtext.ScrolledText(frm_log, wrap="word", height=30)
        self.log.pack(fill="both", expand=True)
        
        self._log(f"SafeMed v2.0 已启动")
        self._log(f"项目根目录: {self.repo_root}")
        self._log(f"词典数量: {len(self.terms)} 个类别")
        
    # ========== 事件处理 ==========
    
    def on_choose_file(self):
        """选择输入文件"""
        path = filedialog.askopenfilename(
            title="选择需要脱敏的文件",
            filetypes=[
                ("支持的格式", "*.txt *.docx *.csv *.xlsx *.xls *.json *.jsonl"),
                ("纯文本", "*.txt"),
                ("Word文档", "*.docx"),
                ("CSV表格", "*.csv"),
                ("Excel表格", "*.xlsx *.xls"),
                ("JSON数据", "*.json"),
                ("JSONL流数据", "*.jsonl"),
                ("所有文件", "*.*"),
            ],
        )
        if not path:
            return
        
        self.input_path.set(path)
        try:
            self.loaded = load_file(path)
            self._log(f"✓ 已加载: {Path(path).name} | 类型={self.loaded.kind}")
            self._refresh_columns_ui()
            self._preview_load_into_left()
        except Exception as e:
            messagebox.showerror("加载失败", f"无法加载文件:\n{str(e)}")
            self._log(f"✗ 加载失败: {str(e)}")
            self._log(traceback.format_exc())
    
    def on_choose_outdir(self):
        """选择输出目录"""
        d = filedialog.askdirectory(title="选择输出目录")
        if not d:
            return
        self.output_dir.set(d)
        self._log(f"✓ 输出目录已设置: {d}")
    
    def _refresh_columns_ui(self):
        """刷新列选择UI"""
        self.cols_list.delete(0, "end")
        self.selected_cols = []
        if not self.loaded or self.loaded.kind != "df":
            return
        cols = get_text_columns(self.loaded.df)
        for c in cols:
            self.cols_list.insert("end", c)
    
    def _preview_load_into_left(self):
        """加载预览到左侧文本框"""
        self.txt_in.delete("1.0", "end")
        self.txt_out.delete("1.0", "end")
        if not self.loaded:
            return
        
        if self.loaded.kind == "text":
            self.txt_in.insert("end", self.loaded.text[:5000])
        elif self.loaded.kind == "docx":
            sample = "\n".join(self.loaded.docx_paragraphs[:min(len(self.loaded.docx_paragraphs), 20)])
            self.txt_in.insert("end", sample[:5000])
        elif self.loaded.kind == "df":
            df = self.loaded.df.head(min(self.preview_rows, 20))
            self.txt_in.insert("end", df.to_string(index=False)[:5000])
        elif self.loaded.kind == "jsonl":
            rows = self.loaded.jsonl_rows[:min(len(self.loaded.jsonl_rows), 10)]
            self.txt_in.insert("end", "\n".join([str(r) for r in rows])[:5000])
    
    def on_preview(self):
        """预览脱敏效果"""
        if not self.loaded:
            messagebox.showwarning("提示", "请先选择输入文件")
            return
        
        try:
            self._do_deidentify(preview_only=True)
        except Exception as e:
            messagebox.showerror("脱敏失败", str(e))
            self._log(f"✗ 脱敏失败: {str(e)}")
    
    def on_run(self):
        """运行脱敏并导出"""
        if not self.loaded:
            messagebox.showwarning("提示", "请先选择输入文件")
            return
        
        if not self.output_dir.get():
            messagebox.showwarning("提示", "请先选择输出目录")
            return
        
        # 在后台线程运行以避免UI冻结
        thread = threading.Thread(target=self._do_deidentify, args=(False,), daemon=True)
        thread.start()
    
    def _highlight_modifications(self, text: str, stats: dict):
        """在文本框中高亮所有修改的内容"""
        import re
        
        # 高亮各类修改内容
        patterns = [
            (r'\[PHONE\]', 'phone'),
            (r'ID_[a-f0-9]+', 'id'),
            (r'某[某某a-zA-Z0-9]*', 'name'),
            (r'\[HOSPITAL\]', 'hospital'),
            (r'\[DEPARTMENT\]', 'hospital'),
            (r'\[FACILITY\]', 'hospital'),
            (r'\d{4}-\d{2}-\d{2}', 'date'),  # 日期格式
            (r'\d+～\d+岁', 'modified'),      # 年龄范围
        ]
        
        for pattern, tag in patterns:
            for match in re.finditer(pattern, text):
                start_idx = f"1.0+{match.start()}c"
                end_idx = f"1.0+{match.end()}c"
                self.txt_out.tag_add(tag, start_idx, end_idx)
    
    def _do_deidentify(self, preview_only: bool = False):
        """执行脱敏操作"""
        self.prog.start()
        try:
            # 脱敏前先保存框内用户的编辑内容
            user_edited_text = self.txt_out.get("1.0", "end").rstrip() if self.txt_out.get("1.0", "end").strip() else None
            
            # 获取脱敏选项
            enable_categories = {
                "id_like": self.enable_id.get(),
                "phone": self.enable_phone.get(),
                "email": self.enable_email.get(),
                "date": self.enable_date.get(),
                "age": self.enable_age.get(),
                "hospital_dict": self.enable_hospital.get(),
                "surnames": self.enable_surnames.get(),
                "doctor_title": self.enable_doctor_title.get(),
                "hospital_suffixes": self.enable_suffixes.get(),
                "custom_terms": self.enable_custom_terms.get(),
            }
            
            # 创建脱敏引擎
            engine = DeidEngine(
                custom_terms=self.terms,
                enable_categories=enable_categories,
                replacement_mode=self.replacement_mode.get(),
                prefer_native_safe_med=self.prefer_native.get(),
            )
            
            if self.loaded.kind == "text":
                deid_text, stats, backend = engine.deidentify_text(self.loaded.text)
                self.deidentified_text = deid_text
                self.deidentified_stats = stats
                self.backend_used = backend
                
                # 仅在预览模式下显示脱敏结果，避免导出时出现闪屏
                if preview_only:
                    self.txt_out.delete("1.0", "end")
                    self.txt_out.insert("end", deid_text[:5000])
                    # 高亮修改的内容
                    self._highlight_modifications(deid_text[:5000], stats)
                
                if not preview_only:
                    # 导出用户编辑后的内容（优先使用脱敏前保存的用户编辑）
                    export_text = user_edited_text if user_edited_text else deid_text
                    
                    out_path = suggest_output_path(self.loaded.path, Path(self.output_dir.get()))
                    save_text(out_path, export_text)
                    
                    # 导出后恢复框内的用户编辑内容（保持框内显示用户编辑的内容）
                    if user_edited_text:
                        self.txt_out.delete("1.0", "end")
                        self.txt_out.insert("end", user_edited_text)
                    
                    self._log(f"✓ 脱敏完成！已保存: {out_path}")
                    messagebox.showinfo("成功", f"文件已脱敏并保存到:\n{out_path}")
                else:
                    self._log(f"✓ 预览完成 | 后端: {backend} | 替换数: {sum(stats.values())}")
                    
            elif self.loaded.kind == "docx":
                deidentified_paras = []
                total_stats = {}
                for para_text in self.loaded.docx_paragraphs:
                    deid_para, stats, _ = engine.deidentify_text(para_text)
                    deidentified_paras.append(deid_para)
                    for k, v in stats.items():
                        total_stats[k] = total_stats.get(k, 0) + v
                
                self.deidentified_text = "\n".join(deidentified_paras[:10])
                self.deidentified_stats = total_stats
                
                # 仅在预览模式下显示脱敏结果，避免导出时出现闪屏
                if preview_only:
                    self.txt_out.delete("1.0", "end")
                    self.txt_out.insert("end", self.deidentified_text[:5000])
                
                if not preview_only:
                    # 导出用户编辑后的内容（优先使用脱敏前保存的用户编辑）
                    if user_edited_text:
                        deidentified_paras[0] = user_edited_text
                    
                    out_path = suggest_output_path(self.loaded.path, Path(self.output_dir.get()))
                    save_docx(out_path, deidentified_paras)
                    
                    # 导出后恢复框内的用户编辑内容
                    if user_edited_text:
                        self.txt_out.delete("1.0", "end")
                        self.txt_out.insert("end", user_edited_text)
                    
                    self._log(f"✓ DOCX脱敏完成！已保存: {out_path}")
                    messagebox.showinfo("成功", f"文件已脱敏并保存到:\n{out_path}")
                else:
                    self._log(f"✓ DOCX预览完成 | 总替换: {sum(total_stats.values())}")
            
            elif self.loaded.kind == "df":
                df = self.loaded.df.copy()
                cols_to_process = self.cols_list.curselection()
                if not cols_to_process:
                    cols_to_process = range(len(df.columns))
                
                cols_names = [self.cols_list.get(i) if i < self.cols_list.size() else df.columns[i] 
                             for i in cols_to_process]
                
                total_stats = {}
                for col in cols_names:
                    if col not in df.columns:
                        continue
                    new_col = []
                    for val in df[col]:
                        deid_val, stats, _ = engine.deidentify_text(str(val))
                        new_col.append(deid_val)
                        for k, v in stats.items():
                            total_stats[k] = total_stats.get(k, 0) + v
                    df[col] = new_col
                
                preview_df = df.head(5)
                # 仅在预览模式下显示脱敏结果，避免导出时出现闪屏
                if preview_only:
                    self.txt_out.delete("1.0", "end")
                    preview_str = preview_df.to_string(index=False)[:5000]
                    self.txt_out.insert("end", preview_str)
                
                # 保存当前DataFrame作为最终导出版本
                self.deidentified_df = df.copy()
                
                if not preview_only:
                    out_path = suggest_output_path(self.loaded.path, Path(self.output_dir.get()))
                    save_df(out_path, self.deidentified_df)
                    self._log(f"✓ 表格脱敏完成！已保存: {out_path}")
                    messagebox.showinfo("成功", f"文件已脱敏并保存到:\n{out_path}")
                else:
                    self._log(f"✓ 表格预览完成 | 处理列数: {len(cols_names)} | 总替换: {sum(total_stats.values())}")
            
            # 更新统计信息
            stats_text = f"脱敏统计 | " + " | ".join([f"{k}:{v}" for k, v in self.deidentified_stats.items()])
            self.stat_label.config(text=stats_text)
            
        except Exception as e:
            self._log(f"✗ 错误: {str(e)}")
            self._log(traceback.format_exc())
            messagebox.showerror("错误", str(e))
        finally:
            self.prog.stop()
    
    # ========== 词典管理 ==========
    
    def refresh_category_list(self):
        """刷新类别列表"""
        self.cat_list.delete(0, "end")
        for k in sorted(self.terms.keys()):
            self.cat_list.insert("end", k)
    
    def refresh_terms_list(self):
        """刷新词条列表"""
        self.term_list.delete(0, "end")
        sel = self.cat_list.curselection()
        if not sel:
            return
        cat = self.cat_list.get(sel[0])
        for t in self.terms.get(cat, []):
            self.term_list.insert("end", t)
    
    def on_add_category(self):
        """新增类别"""
        from tkinter.simpledialog import askstring
        name = askstring("新增类别", "输入新类别名称（如: hospitals, surnames等）：")
        if not name:
            return
        name = name.strip().lower()
        if not name:
            return
        if name in self.terms:
            messagebox.showwarning("提示", f"类别 '{name}' 已存在")
            return
        self.terms[name] = []
        self.refresh_category_list()
        self._log(f"✓ 新增类别: {name}")
    
    def on_del_category(self):
        """删除类别"""
        sel = self.cat_list.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先选择要删除的类别")
            return
        cat = self.cat_list.get(sel[0])
        if messagebox.askyesno("确认", f"确定删除类别 '{cat}' 及其所有词条吗？"):
            del self.terms[cat]
            self.refresh_category_list()
            self._log(f"✓ 已删除类别: {cat}")
    
    def on_add_term(self):
        """添加词条"""
        sel = self.cat_list.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一个类别")
            return
        
        from tkinter.simpledialog import askstring
        term = askstring("添加词条", "输入新词条：")
        if not term:
            return
        term = term.strip()
        if not term:
            return
        
        cat = self.cat_list.get(sel[0])
        if term not in self.terms[cat]:
            self.terms[cat].append(term)
            self.refresh_terms_list()
            self._log(f"✓ 添加词条: {cat}/{term}")
    
    def on_del_term(self):
        """删除词条"""
        sel = self.term_list.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先选择要删除的词条")
            return
        
        cat_sel = self.cat_list.curselection()
        if not cat_sel:
            return
        
        term = self.term_list.get(sel[0])
        cat = self.cat_list.get(cat_sel[0])
        
        if term in self.terms[cat]:
            self.terms[cat].remove(term)
            self.refresh_terms_list()
            self._log(f"✓ 删除词条: {cat}/{term}")
    
    def on_import_terms(self):
        """从TXT批量导入词条"""
        sel = self.cat_list.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一个类别")
            return
        
        path = filedialog.askopenfilename(
            title="选择词条文本文件",
            filetypes=[("Text files", "*.txt"), ("All", "*.*")]
        )
        if not path:
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            cat = self.cat_list.get(sel[0])
            added = 0
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and line not in self.terms[cat]:
                    self.terms[cat].append(line)
                    added += 1
            
            self.refresh_terms_list()
            messagebox.showinfo("成功", f"导入了 {added} 个新词条")
            self._log(f"✓ 从 {Path(path).name} 导入 {added} 个词条到 {cat}")
        except Exception as e:
            messagebox.showerror("导入失败", str(e))
            self._log(f"✗ 导入失败: {str(e)}")
    
    def on_save_terms(self):
        """保存词典"""
        try:
            self.store.save_terms(self.terms)
            messagebox.showinfo("成功", "词典已保存")
            self._log("✓ 词典已保存")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))
            self._log(f"✗ 保存失败: {str(e)}")
    
    # ========== 帮助 ==========
    
    def _log(self, msg: str):
        """添加日志"""
        self.log.insert("end", msg + "\n")
        self.log.see("end")
    
    def show_help(self):
        """显示使用说明"""
        help_text = """
SafeMed 文本脱敏工具 v2.0 使用说明
================================

【功能介绍】
- 支持多种文件格式：TXT、DOCX、CSV、XLSX、JSON、JSONL
- 自动识别和替换敏感信息：身份证、手机号、邮箱、日期、医院名称等
- 支持自定义词典，灵活配置脱敏规则
- 实时预览脱敏效果

【基本使用】
1. 选择输入文件（支持多种格式）
2. 选择输出目录
3. 配置脱敏选项（选择要脱敏的信息类型）
4. 点击"预览脱敏"查看效果
5. 点击"开始脱敏并导出"进行完整脱敏和保存

【脱敏选项说明】
- 身份证号：识别18位身份证号码
- 手机号：识别11位手机号码
- 邮箱：识别电子邮箱地址
- 日期：识别各种日期格式（YYYY-MM-DD等）
- 医院名称：使用词典识别医院名称
- 自定义词典：使用用户自定义的敏感词列表

【词典管理】
- 在"词典管理"标签页中添加、删除或修改词条
- 支持批量导入TXT格式的词条文件
- 修改后必须点击"保存"才能生效

【替换模式】
- 标签模式：将敏感信息替换为 [ID]、[PHONE] 等标签
- 掩码模式：将敏感信息替换为 [****] 等掩码

【结构化数据】
对于CSV、XLSX等表格文件，可以选择只脱敏特定列。
        """
        messagebox.showinfo("使用说明", help_text)
    
    def show_about(self):
        """显示关于信息"""
        messagebox.showinfo(
            "关于",
            "SafeMed 文本脱敏工具 v2.0\n\n"
            "用于医学文本中敏感信息的自动识别和脱敏\n\n"
            "支持多种文件格式和灵活的脱敏规则"
        )


def main():
    """主程序入口"""
    app = ModernSafeMedApp()
    app.mainloop()


if __name__ == "__main__":
    main()
