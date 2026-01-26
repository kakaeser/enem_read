from backend.config.db_init import init_db
init_db()

from frontend.app import App

def main():
    
    app = App()
    app.mainloop()
  
if __name__ == "__main__":
    main()
