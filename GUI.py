import customtkinter as ctk
import threading
import asyncio
from Scraper import run_all_queries

# -------------------- GUI CONFIG --------------------
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class ScraperGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Physics Scraper")
        self.geometry("520x420")
        self.resizable(False, False)

        # -------------------- TITLE --------------------
        self.title_label = ctk.CTkLabel(
            self,
            text="Physics & Astronomy Scraper",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.pack(pady=15)

        # -------------------- QUERY BOX --------------------
        self.query_label = ctk.CTkLabel(self, text="Search Queries (one per line):")
        self.query_label.pack(anchor="w", padx=20)

        self.query_textbox = ctk.CTkTextbox(self, height=120)
        self.query_textbox.pack(fill="x", padx=20, pady=5)

        default_queries = [
            "Physics and astronomy",
            "Astrophysics",
            "Quantum mechanics",
            "Cosmology"
        ]
        self.query_textbox.insert("1.0", "\n".join(default_queries))

        # -------------------- OPTIONS --------------------
        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.pack(fill="x", padx=20, pady=10)

        self.scroll_label = ctk.CTkLabel(self.options_frame, text="Max Scrolls:")
        self.scroll_label.pack(side="left", padx=10)

        self.scroll_entry = ctk.CTkEntry(self.options_frame, width=60)
        self.scroll_entry.insert(0, "3")
        self.scroll_entry.pack(side="left")

        # -------------------- RUN BUTTON --------------------
        self.run_button = ctk.CTkButton(
            self,
            text="Run Scraper",
            command=self.start_scraper
        )
        self.run_button.pack(pady=15)

        # -------------------- PROGRESS --------------------
        self.progress = ctk.CTkProgressBar(self)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=20, pady=10)

        # -------------------- OUTPUT --------------------
        self.output_label = ctk.CTkLabel(
            self,
            text="Status: Idle",
            font=ctk.CTkFont(size=14)
        )
        self.output_label.pack(pady=10)

    # -------------------- SCRAPER THREAD --------------------
    def start_scraper(self):
        self.run_button.configure(state="disabled")
        self.progress.set(0.2)
        self.output_label.configure(text="Status: Running...")

        thread = threading.Thread(target=self.run_async_scraper, daemon=True)
        thread.start()

    def run_async_scraper(self):
        queries = self.query_textbox.get("1.0", "end").strip().splitlines()
        max_scrolls = int(self.scroll_entry.get())

        results = asyncio.run(run_all_queries(queries, max_scrolls=max_scrolls))

        final_data = {
            'Usernames': [],
            'DisplayNames': [],
            'VerifiedStatus': []
        }
        seen = set()

        for data in results:
            for u, d, v in zip(
                data['Usernames'],
                data['DisplayNames'],
                data['VerifiedStatus']
            ):
                if u not in seen:
                    seen.add(u)
                    final_data['Usernames'].append(u)
                    final_data['DisplayNames'].append(d)
                    final_data['VerifiedStatus'].append(v)

        self.after(0, self.update_ui, len(final_data['Usernames']))

    def update_ui(self, total):
        self.progress.set(1)
        self.output_label.configure(
            text=f"Completed: {total} unique users found"
        )
        self.run_button.configure(state="normal")


# -------------------- RUN APP --------------------
if __name__ == "__main__":
    app = ScraperGUI()
    app.mainloop()
