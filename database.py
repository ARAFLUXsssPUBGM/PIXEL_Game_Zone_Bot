import sqlite3
import os
class Database:
    def __init__(self, db_path="pixel_bot.db"):
        self.db_path = db_path
        self._init_db()
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create admins table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    chat_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)
            
            # Create tournaments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tournaments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_name TEXT NOT NULL,
                    total_slots INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active'
                )
            """)
            
            # Create registrations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournament_id INTEGER NOT NULL,
                    team_name TEXT NOT NULL,
                    captain_name TEXT NOT NULL,
                    captain_phone TEXT NOT NULL,
                    members TEXT NOT NULL, -- JSON string or comma-separated player names
                    user_id INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
                )
            """)
            
            conn.commit()
    # --- ADMIN METHODS ---
    
    def add_admin(self, chat_id, name):
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO admins (chat_id, name) VALUES (?, ?)",
                    (chat_id, name)
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
    def remove_admin(self, chat_id):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM admins WHERE chat_id = ?", (chat_id,))
            conn.commit()
            return True
    def is_admin(self, chat_id, main_admin_id):
        if str(chat_id) == str(main_admin_id):
            return True
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT 1 FROM admins WHERE chat_id = ?", (chat_id,))
            return cursor.fetchone() is not None
    def get_admins(self):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT chat_id, name FROM admins")
            return [dict(row) for row in cursor.fetchall()]
    # --- TOURNAMENT METHODS ---
    
    def create_tournament(self, game_name, total_slots):
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO tournaments (game_name, total_slots) VALUES (?, ?)",
                (game_name, total_slots)
            )
            conn.commit()
            return cursor.lastrowid
    def get_active_tournaments(self):
        with self._get_connection() as conn:
            # We also calculate how many slots are filled
            cursor = conn.execute("""
                SELECT t.id, t.game_name, t.total_slots, t.status,
                       (SELECT COUNT(*) FROM registrations r WHERE r.tournament_id = t.id) as filled_slots
                FROM tournaments t
                WHERE t.status = 'active'
            """)
            return [dict(row) for row in cursor.fetchall()]
    def get_all_tournaments(self):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT t.id, t.game_name, t.total_slots, t.status,
                       (SELECT COUNT(*) FROM registrations r WHERE r.tournament_id = t.id) as filled_slots
                FROM tournaments t
                ORDER BY t.id DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    def get_tournament(self, tournament_id):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT t.id, t.game_name, t.total_slots, t.status,
                       (SELECT COUNT(*) FROM registrations r WHERE r.tournament_id = t.id) as filled_slots
                FROM tournaments t
                WHERE t.id = ?
            """, (tournament_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    def close_tournament(self, tournament_id):
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE tournaments SET status = 'completed' WHERE id = ?",
                (tournament_id,)
            )
            conn.commit()
            return True
    # --- REGISTRATION METHODS ---
    
    def register_team(self, tournament_id, team_name, captain_name, captain_phone, members_list, user_id):
        # members_list is a list of strings: ["player2", "player3", "player4", "player5"]
        # we join them with a comma or save as JSON
        import json
        members_str = json.dumps(members_list)
        
        # Check if tournament is active and has free slots
        tournament = self.get_tournament(tournament_id)
        if not tournament or tournament['status'] != 'active':
            return False, "Turnir faol emas."
            
        if tournament['filled_slots'] >= tournament['total_slots']:
            return False, "Ushbu turnirda bo'sh slotlar qolmagan."
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO registrations (tournament_id, team_name, captain_name, captain_phone, members, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tournament_id, team_name, captain_name, captain_phone, members_str, user_id))
            conn.commit()
            
            # Check if now full
            updated_tournament = self.get_tournament(tournament_id)
            is_now_full = updated_tournament['filled_slots'] >= updated_tournament['total_slots']
            
            return True, {
                "is_now_full": is_now_full,
                "game_name": updated_tournament['game_name'],
                "filled_slots": updated_tournament['filled_slots'],
                "total_slots": updated_tournament['total_slots']
            }
    def get_registrations(self, tournament_id):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, tournament_id, team_name, captain_name, captain_phone, members, user_id, timestamp
                FROM registrations
                WHERE tournament_id = ?
                ORDER BY id ASC
            """, (tournament_id,))
            
            import json
            results = []
            for row in cursor.fetchall():
                d = dict(row)
                try:
                    d['members'] = json.loads(d['members'])
                except Exception:
                    d['members'] = d['members'].split(",")
                results.append(d)
            return results
    def get_all_registered_users(self):
        # Returns all unique telegram user_ids who interacted or registered
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT DISTINCT user_id FROM registrations")
            return [row['user_id'] for row in cursor.fetchall()]
    # --- STATS METHOD ---
    
    def get_stats(self):
        with self._get_connection() as conn:
            total_tournaments = conn.execute("SELECT COUNT(*) FROM tournaments").fetchone()[0]
            active_tournaments = conn.execute("SELECT COUNT(*) FROM tournaments WHERE status = 'active'").fetchone()[0]
            completed_tournaments = conn.execute("SELECT COUNT(*) FROM tournaments WHERE status = 'completed'").fetchone()[0]
            total_teams = conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0]
            
            # Total unique players registered (5 players per team)
            total_players = total_teams * 5
            
            # Count per game
            games_cursor = conn.execute("""
                SELECT game_name, COUNT(*) as team_count 
                FROM tournaments t
                JOIN registrations r ON t.id = r.tournament_id
                GROUP BY game_name
            """)
            games_stats = {row['game_name']: row['team_count'] for row in games_cursor.fetchall()}
            
            return {
                "total_tournaments": total_tournaments,
                "active_tournaments": active_tournaments,
                "completed_tournaments": completed_tournaments,
                "total_teams": total_teams,
                "total_players": total_players,
                "games_stats": games_stats
            }
