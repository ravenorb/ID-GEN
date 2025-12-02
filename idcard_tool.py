import os
import random
import string
from datetime import datetime, date
import calendar
import tkinter as tk
from tkinter import ttk, messagebox
import re

import pdf417gen
from barcode import Code128
from barcode.writer import ImageWriter


# ======================================================
#  HELPER FUNCTIONS
# ======================================================

def clean_alpha(value: str, max_len: int, allow_spaces: bool = False) -> str:
    if value is None:
        value = ""
    value = value.strip()
    allowed = string.ascii_letters + (" " if allow_spaces else "")
    filtered = "".join(ch for ch in value if ch in allowed)
    return filtered.upper()[:max_len]


def clean_alnum(value: str, max_len: int, allow_spaces: bool = True) -> str:
    if value is None:
        value = ""
    value = value.strip()
    allowed = string.ascii_letters + string.digits + (" " if allow_spaces else "")
    filtered = "".join(ch for ch in value if ch in allowed)
    return filtered.upper()[:max_len]


def clean_numeric(value: str, required_len=None, max_len=None) -> str:
    if value is None:
        value = ""
    digits = "".join(ch for ch in value if ch.isdigit())
    if required_len is not None and len(digits) != required_len:
        raise ValueError(f"Must be exactly {required_len} digits.")
    if max_len is not None and len(digits) > max_len:
        raise ValueError(f"Must be at most {max_len} digits.")
    return digits


def parse_mmddyyyy(text: str, field_name: str) -> date:
    text = text.strip()
    try:
        dt = datetime.strptime(text, "%m/%d/%Y")
    except ValueError:
        raise ValueError(f"{field_name} must be in MM/DD/YYYY format.")
    return dt.date()


def format_mmddyyyy(d: date) -> str:
    return d.strftime("%m/%d/%Y")


def format_mmddyyyy_compact(d: date) -> str:
    """MMDDYYYY without separators."""
    return d.strftime("%m%d%Y")


def add_years_safe(d: date, years: int) -> date:
    """Add years, clamping day for Feb 29 etc."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        last_day = calendar.monthrange(d.year + years, d.month)[1]
        return date(d.year + years, d.month, last_day)


def exp_from_dob_iss(dob: date, iss: date) -> date:
    """EXP = same month/day as DOB, year = ISS.year + 8."""
    target_year = iss.year + 8
    m = dob.month
    day = dob.day
    try:
        return date(target_year, m, day)
    except ValueError:
        last_day = calendar.monthrange(target_year, m)[1]
        return date(target_year, m, last_day)


def pad_left(value: int | str, total_len: int, pad_char="0") -> str:
    return str(value).rjust(total_len, pad_char)


def random_numeric(length: int) -> str:
    return "".join(random.choice(string.digits) for _ in range(length))


def apply_escape_sequences(s: str) -> str:
    """
    Convert literal:
        \\n  -> newline
        \\r  -> carriage return
        \\xNN -> ASCII byte NN
    """
    if s is None:
        return ""
    s = s.replace("\\n", "\n").replace("\\r", "\r")

    def repl_hex(m):
        return chr(int(m.group(1), 16))

    s = re.sub(r"\\x([0-9A-Fa-f]{2})", repl_hex, s)
    return s


# ======================================================
#  CORE GENERATION
# ======================================================

def generate_outputs(data: dict, output_root: str):
    vars_: dict[str, str] = {}

    # ----------------------- INPUT VALIDATION -----------------------
    dln = clean_numeric(data["varDLN"], required_len=8)
    vars_["varDLN"] = dln

    # Names
    first = clean_alpha(data["varFIRST"], 30)
    if not (3 <= len(first) <= 30):
        raise ValueError("FIRST must be 3–30 alphabetic characters.")
    mid = clean_alpha(data["varMID"], 30)
    if not (3 <= len(mid) <= 30):
        raise ValueError("MIDDLE must be 3–30 alphabetic characters.")
    last = clean_alpha(data["varLAST"], 30)
    if not (3 <= len(last) <= 30):
        raise ValueError("LAST must be 3–30 alphabetic characters.")

    vars_["varFIRST"] = first
    vars_["varMID"] = mid
    vars_["varLAST"] = last

    # Dates — input as MM/DD/YYYY
    dob_dt = parse_mmddyyyy(data["varDOB"], "DOB")
    fiss_dt = parse_mmddyyyy(data["varFISS"], "FIRST ISSUE")
    iss_dt = parse_mmddyyyy(data["varISS"], "ISSUE")
    exp_dt = parse_mmddyyyy(data["varEXP"], "EXPIRE")

    # Human-readable versions (for CSV)
    vars_["vardDOB"] = format_mmddyyyy(dob_dt)
    vars_["vardFISS"] = format_mmddyyyy(fiss_dt)
    vars_["vardISS"] = format_mmddyyyy(iss_dt)
    vars_["vardEXP"] = format_mmddyyyy(exp_dt)

    # Compact AAMVA versions (for PDF417)
    vars_["varDOB"] = format_mmddyyyy_compact(dob_dt)
    vars_["varFISS"] = format_mmddyyyy_compact(fiss_dt)
    vars_["varISS"] = format_mmddyyyy_compact(iss_dt)
    vars_["varEXP"] = format_mmddyyyy_compact(exp_dt)

    # First issue ≥ DOB + 14
    dob_plus_14 = add_years_safe(dob_dt, 14)
    if fiss_dt < dob_plus_14:
        raise ValueError("FIRST ISSUE must be at least 14 years after DOB.")

    # ISSUE ≥ FIRST ISSUE
    if iss_dt < fiss_dt:
        raise ValueError("ISSUE DATE cannot be before FIRST ISSUE DATE.")

    # EXP matches DOB's month/day, ISS.year + 8
    expected_exp = exp_from_dob_iss(dob_dt, iss_dt)
    if exp_dt != expected_exp:
        raise ValueError("EXPIRE must be DOB's month/day with year = ISS.year + 8.")

    # Address
    vars_["varADD"] = clean_alnum(data["varADD"], 30)
    city = clean_alpha(data["varCITY"], 30)
    if not (3 <= len(city) <= 30):
        raise ValueError("CITY must be 3–30 alphabetic characters.")
    vars_["varCITY"] = city

    # ZIP + FOUR
    vars_["varZIP"] = clean_numeric(data["varZIP"], required_len=5)
    vars_["varFOUR"] = clean_numeric(data["varFOUR"], required_len=4)

    # Race / Sex
    race_map = {"WHITE": "W", "BLACK": "BK", "HISPANIC": "H"}
    vars_["varRACE"] = race_map[data["varRACE"]]

    sex = data["varSEX"].upper().strip()
    if sex not in ("M", "F"):
        raise ValueError("SEX must be M or F.")
    vars_["varSEX"] = sex

    # Height
    feet = int(clean_numeric(data["varFEET"], max_len=1))
    inch = int(clean_numeric(data["varINCH"], max_len=2))
    if not (3 <= feet <= 7):
        raise ValueError("FEET must be 3–7.")
    if not (0 <= inch <= 11):
        raise ValueError("INCH must be 0–11.")
    vars_["varFEET"] = str(feet)
    vars_["varINCH"] = str(inch)
    vars_["varHGHT"] = str(feet * 12 + inch)

    vars_["varWGHT"] = pad_left(clean_numeric(data["varWGHT"], max_len=3), 3)
    vars_["varEYES"] = data["varEYES"]
    vars_["varHAIR"] = data["varHAIR"]

    # DD / INV / REST / END — defaults applied earlier in UI
    vars_["varDD"] = "".join(ch for ch in data["varDD"] if ch.isdigit())
    vars_["varINV"] = "".join(ch for ch in data["varINV"] if ch.isdigit())
    vars_["varREST"] = data["varREST"]
    vars_["varEND"] = data["varEND"]

    vars_["varSTATE"] = "TX"
    vars_["varCOUNTRY"] = "USA"
    vars_["vareSEX"] = "2" if vars_["varSEX"] == "F" else "1"
    vars_["varCLASS"] = "C"
    vars_["varCOMP"] = "F"
    vars_["varZIP4"] = vars_["varZIP"] + vars_["varFOUR"]

    # NAME = FIRST + MIDDLE (no LAST)
    name_parts = [vars_["varFIRST"], vars_["varMID"]]
    vars_["varNAME"] = " ".join([p for p in name_parts if p])
    # ----------------------- PDF417 FIELD SET -----------------------
    fields = {}
    f = fields

    # AAMVA-compliant values
    f["DAQ"] = "DAQ00" + vars_["varDLN"]
    f["DAC"] = "DAC" + vars_["varFIRST"]
    f["DDF"] = "DDF" + vars_["varFIRST"][:30]
    f["DAD"] = "DAD" + vars_["varMID"]
    f["DDG"] = "DDG" + vars_["varMID"][:30]
    f["DCS"] = "DCS" + vars_["varLAST"]
    f["DDE"] = "DDE" + vars_["varLAST"][:30]
    f["DBB"] = "DBB" + vars_["varDOB"]     # compact
    f["DAG"] = "DAG" + vars_["varADD"]
    f["DAI"] = "DAI" + vars_["varCITY"]
    f["DAJ"] = "DAJ" + vars_["varSTATE"]
    f["DAK"] = "DAK" + vars_["varZIP4"]
    f["DDB"] = "DDB" + vars_["varFISS"]
    f["DBD"] = "DBD" + vars_["varISS"]
    f["DBA"] = "DBA" + vars_["varEXP"]
    f["DCL"] = "DCL" + vars_["varRACE"]
    f["DBC"] = "DBC" + vars_["vareSEX"]
    f["DAU"] = "DAU" + vars_["varHGHT"] + " IN"
    f["DAW"] = "DAW" + vars_["varWGHT"]
    f["DAY"] = "DAY" + vars_["varEYES"]
    f["DAZ"] = "DAZ" + vars_["varHAIR"]
    f["DCF"] = "DCF" + vars_["varDD"]
    f["DCG"] = "DCG" + vars_["varCOUNTRY"]
    f["DCB"] = "DCB" + vars_["varREST"]
    f["DCD"] = "DCD" + vars_["varEND"]
    f["DDA"] = "DDA" + vars_["varCOMP"]
    f["DCK"] = "DCK" + vars_["varINV"]
    f["DCA"] = "DCA" + vars_["varCLASS"]

    # Required ORDER
    order = [
        "DCA","DCD","DCB","DBA","DCS","DDE","DAC","DDF","DAD","DDG","DBD","DBB",
        "DBC","DAY","DAU","DAG","DAI","DAJ","DAK","DAQ","DCF","DCG","DAZ","DCK",
        "DCL","DDA","DDB","DAW"
    ]

    pdfinfo = ""
    for key in order:
        pdfinfo += f[key] + "\n"
    pdfinfo += "DDK1\n\rZTZTAN\n\r"

    vars_["varDATA_PDF417INFO"] = pdfinfo

    # DATALEN = len(info) - 85
    datalen_minus = max(0, len(pdfinfo) - 85)
    vars_["varDATALEN"] = pad_left(datalen_minus, 4)

    # ZTSTART = 41 + DATALEN
    vars_["varZTSTART"] = pad_left(41 + datalen_minus, 4)

    # Complete PDF417 data block with decoded control characters
    prefix_literal = "@\\n\\x1e\\rANSI636015080001DL0041"
    full_pdf417_literal = (
        prefix_literal +
        vars_["varDATALEN"] +
        "ZT" +
        vars_["varZTSTART"] +
        "0007DL" +
        pdfinfo
    )
    vars_["varDATA_PDF417"] = apply_escape_sequences(full_pdf417_literal)

    # ------------------ CSV BUILD (alphabetical, no trailing comma) --------------------
    csv_header_list = [
        "ADD","CLASS","CITY","DD","DLN","DOB","DOB2","END","EYES","EXP",
        "FEET","FOUR","INCH","INV","ISS","LAST","NAME","REST","SEX","STATE","ZIP"
    ]
    vars_["varDATA_CSV1"] = ",".join(csv_header_list)

    csv_data_list = [
        vars_["varADD"],
        vars_["varCLASS"],
        vars_["varCITY"],
        vars_["varDD"],
        vars_["varDLN"],
        vars_["vardDOB"],     # DOB
        vars_["varDOB"],      # DOB2
        vars_["varEND"],
        vars_["varEYES"],
        vars_["vardEXP"],
        vars_["varFEET"],
        vars_["varFOUR"],
        vars_["varINCH"],
        vars_["varINV"],
        vars_["vardISS"],
        vars_["varLAST"],
        vars_["varNAME"],     # ONLY FIRST + MIDDLE
        vars_["varREST"],
        vars_["varSEX"],
        vars_["varSTATE"],
        vars_["varZIP"],
    ]
    vars_["varDATA_CSV2"] = ",".join(csv_data_list)

    # ------------------ WRITE OUTPUT FILES --------------------
    base = vars_["varDLN"]
    dlndir = os.path.join(output_root, base)
    os.makedirs(dlndir, exist_ok=True)

    csv_path = os.path.join(dlndir, "data.csv")
    with open(csv_path, "w", encoding="utf-8") as f_out:
        f_out.write(vars_["varDATA_CSV1"] + "\n")
        f_out.write(vars_["varDATA_CSV2"] + "\n")

    # PDF417 image
    codes = pdf417gen.encode(vars_["varDATA_PDF417"], columns=17, security_level=5)
    img = pdf417gen.render_image(codes, scale=2, ratio=4)
    pdf417_path = os.path.join(dlndir, "pdf417.png")
    img.save(pdf417_path)

    # Code128 (inventory)
    barcode = Code128(vars_["varINV"], writer=ImageWriter())
    code128_path = barcode.save(
        os.path.join(dlndir, "code128"),
        options={"write_text": False}
    )

    return {
        "csv": csv_path,
        "pdf417": pdf417_path,
        "code128": code128_path,
        "vars": vars_,
        "outdir": dlndir,
    }
# ======================================================
#  TKINTER UI WITH LIVE VALIDATION & AUTOFILL
# ======================================================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ID Card Generator")
        self.resizable(False, False)

        self.vars = {}
        self.entries = {}
        self.field_types = {}
        self.exp_user_edited = False

        fields = [
            ("varDLN","DLN (8 digits)","numeric"),
            ("varFIRST","FIRST","alpha"),
            ("varMID","MIDDLE","alpha"),
            ("varLAST","LAST","alpha"),
            ("varDOB","DOB (MM/DD/YYYY)","date"),
            ("varADD","ADDRESS","any"),
            ("varCITY","CITY","alpha"),
            ("varZIP","ZIP (5)","numeric"),
            ("varFOUR","FOUR (4)","numeric"),
            ("varFISS","FIRST ISSUE (MM/DD/YYYY)","date"),
            ("varISS","ISSUE (MM/DD/YYYY)","date"),
            ("varEXP","EXPIRE (MM/DD/YYYY)","date"),
            ("varRACE","RACE","dropdown_race"),
            ("varSEX","SEX","dropdown_sex"),
            ("varFEET","FEET","numeric"),
            ("varINCH","INCHES","numeric"),
            ("varWGHT","WEIGHT","numeric"),
            ("varEYES","EYES","dropdown_eyes"),
            ("varHAIR","HAIR","dropdown_hair"),
            ("varDD","DD (20 digits or blank)","numeric_blank"),
            ("varREST","RESTRICTION (or blank)","alpha_blank"),
            ("varEND","ENDORSEMENT (or blank)","alpha_blank"),
            ("varINV","INVENTORY # (10 digits or blank)","numeric_blank"),
        ]

        self.race_vals=["WHITE","BLACK","HISPANIC"]
        self.sex_vals=["M","F"]
        self.eyes_vals=["HAZ","BLU","BLK","BRO","GRN"]
        self.hair_vals=["BRO","BLK","BLO","GRY","RED"]

        main=ttk.Frame(self,padding=10)
        main.grid(row=0,column=0)

        left=ttk.Frame(main)
        right=ttk.Frame(main)
        left.grid(row=0,column=0,padx=10)
        right.grid(row=0,column=1,padx=10)

        half=len(fields)//2
        for i,(vn,label,ftype) in enumerate(fields[:half]):
            self.make_field(left,i,vn,label,ftype)
        for i,(vn,label,ftype) in enumerate(fields[half:],start=0):
            self.make_field(right,i,vn,label,ftype)

        ttk.Button(main,text="Generate",command=self.on_generate)\
            .grid(row=1,column=0,sticky="ew",pady=4)
        ttk.Button(main,text="Debug",command=self.on_debug)\
            .grid(row=1,column=1,sticky="ew",pady=4)

        self.status=tk.StringVar(value="Ready.")
        ttk.Label(main,textvariable=self.status).grid(row=2,column=0,columnspan=2,sticky="w")

    # ---- Field Builder ----
    def make_field(self,parent,row,varname,label,ftype):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky="w",pady=2)
        sv=tk.StringVar()
        self.vars[varname]=sv
        self.field_types[varname]=ftype

        if ftype.startswith("dropdown"):
            if ftype=="dropdown_race":
                vals=self.race_vals
            elif ftype=="dropdown_sex":
                vals=self.sex_vals
            elif ftype=="dropdown_eyes":
                vals=self.eyes_vals
            else:
                vals=self.hair_vals
            cb=ttk.Combobox(parent,textvariable=sv,values=vals,state="readonly",width=18)
            cb.current(0)
            cb.grid(row=row,column=1)
            return

        e=tk.Entry(parent,textvariable=sv,width=21)
        e.grid(row=row,column=1)
        self.entries[varname]=e

        if varname=="varEXP":
            e.bind("<KeyRelease>",lambda ev,vn=varname:self.on_exp_edited(vn))
        else:
            e.bind("<KeyRelease>",lambda ev,vn=varname:self.validate_field(vn))
        e.bind("<FocusOut>",lambda ev,vn=varname:self.validate_field(vn))

    # ---- EXP edited ----
    def on_exp_edited(self,varname):
        self.exp_user_edited=True
        self.validate_field(varname)

    # -------- Soft parse date --------
    def _soft_parse_date(self,text):
        text=text.strip()
        if not text: return None
        try:
            return datetime.strptime(text,"%m/%d/%Y").date()
        except:
            return None

    # -------- Validation engine --------
    def validate_field(self,varname):
        ftype=self.field_types.get(varname)
        if ftype is None: return

        val=self.vars[varname].get().strip()
        widget=self.entries.get(varname)

        if ftype.startswith("dropdown"): return

        # Basic type checks
        valid=True
        if ftype in ("numeric","numeric_blank"):
            valid = val.isdigit() if val!="" else (ftype=="numeric_blank")
        elif ftype=="alpha":
            valid=val.isalpha() and (3<=len(val)<=30)
        elif ftype=="alpha_blank":
            valid=(val=="" or val.isalpha())
        elif ftype=="date":
            valid=self._soft_parse_date(val) is not None

        # Additional rules
        if valid and val!="":
            if varname=="varDLN":
                valid=val.isdigit() and len(val)==8
            elif varname=="varZIP":
                valid=val.isdigit() and len(val)==5
            elif varname=="varFOUR":
                valid=val.isdigit() and len(val)==4
            elif varname=="varFEET":
                valid=val.isdigit() and 3<=int(val)<=7
            elif varname=="varINCH":
                valid=val.isdigit() and 0<=int(val)<=11

        # Date logic
        dob=self._soft_parse_date(self.vars["varDOB"].get())
        fiss=self._soft_parse_date(self.vars["varFISS"].get())
        iss=self._soft_parse_date(self.vars["varISS"].get())
        exp=self._soft_parse_date(self.vars["varEXP"].get())

        # Autofill ISS from FISS if blank
        if varname=="varFISS" and fiss:
            if self.vars["varISS"].get().strip()=="":
                self.vars["varISS"].set(format_mmddyyyy(fiss))
                iss=fiss

        # Autofill EXP unless user modified it
        if dob and iss and not self.exp_user_edited and varname in ("varDOB","varISS"):
            expected=exp_from_dob_iss(dob,iss)
            self.vars["varEXP"].set(format_mmddyyyy(expected))
            exp=expected

        # EXP semantic correctness
        if dob and iss and exp:
            expected=exp_from_dob_iss(dob,iss)
            if exp!=expected and self.entries.get("varEXP"):
                self.entries["varEXP"].configure(bg="lightcoral")
            elif self.entries.get("varEXP"):
                self.entries["varEXP"].configure(bg="lightgreen")

        # Color this field
        if widget:
            if val=="" and ftype.endswith("_blank"):
                widget.configure(bg="white")
            else:
                widget.configure(bg="lightgreen" if valid else "lightcoral")

    # ---- Defaults applied only before Generate/Debug ----
    def _prepare_common_defaults(self):
        if self.vars["varREST"].get().strip()=="":
            self.vars["varREST"].set("NONE")
        if self.vars["varEND"].get().strip()=="":
            self.vars["varEND"].set("NONE")
        if self.vars["varDD"].get().strip()=="":
            self.vars["varDD"].set(random_numeric(20))
        if self.vars["varINV"].get().strip()=="":
            self.vars["varINV"].set(random_numeric(10))

    # ---- Generate ----
    def on_generate(self):
        try:
            self._prepare_common_defaults()
            data={k:v.get() for k,v in self.vars.items()}
            out_root=os.path.join(os.path.dirname(__file__),"output")
            result=generate_outputs(data,out_root)
            self.status.set("Success.")
            messagebox.showinfo("Complete",
                f"Output folder:\n{result['outdir']}\n\nCSV:\n{result['csv']}\n"
                f"PDF417:\n{result['pdf417']}\nCode128:\n{result['code128']}")
        except Exception as e:
            self.status.set("Error.")
            messagebox.showerror("Error",str(e))

    # ---- Debug ----
    def on_debug(self):
        try:
            self._prepare_common_defaults()
            data={k:v.get() for k,v in self.vars.items()}
            out_root=os.path.join(os.path.dirname(__file__),"output")
            result=generate_outputs(data,out_root)
            vars_=result["vars"]

            dbg=tk.Toplevel(self)
            dbg.title("Debug")
            dbg.geometry("900x600")
            text=tk.Text(dbg,wrap="none")
            text.pack(side="left",fill="both",expand=True)
            sb=ttk.Scrollbar(dbg,orient="vertical",command=text.yview)
            sb.pack(side="right",fill="y")
            text.configure(yscrollcommand=sb.set)

            def pl(k,v): text.insert("end",f"{k}: {v}\n")

            text.insert("end","--- BASIC ---\n")
            for key in ["varDLN","varFIRST","varMID","varLAST","vardDOB","varDOB",
                        "vardISS","varISS","vardEXP","varEXP",
                        "varADD","varCITY","varSTATE","varZIP4",
                        "varSEX","vareSEX","varRACE",
                        "varHGHT","varWGHT","varEYES","varHAIR",
                        "varDD","varREST","varEND","varINV","varCLASS"]:
                pl(key,vars_.get(key,""))

            text.insert("end","\n--- PDF417 ---\n")
            pl("DATA_PDF417INFO length",len(vars_["varDATA_PDF417INFO"]))
            pl("DATALEN",vars_["varDATALEN"])
            pl("ZTSTART",vars_["varZTSTART"])
            text.insert("end",repr(vars_["varDATA_PDF417INFO"])+"\n\n")
            text.insert("end","DATA_PDF417 (partial):\n")
            text.insert("end",repr(vars_["varDATA_PDF417"][:400])+"\n\n")

            text.insert("end","--- FILES ---\n")
            pl("CSV",result["csv"])
            pl("PDF417",result["pdf417"])
            pl("Code128",result["code128"])

        except Exception as e:
            messagebox.showerror("Debug Error",str(e))


# ======================================================
# MAIN
# ======================================================

if __name__=="__main__":
    app=App()
    app.mainloop()
