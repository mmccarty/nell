from datetime import datetime, timedelta
import os, sys

def getdt(db, b):
    try:
        date, time     = b.split("_")
        year, mon, day = date.replace(db + ".", "").split("-")
        hour           = time.split(":")[0]
    except ValueError:
        return None
    return datetime(int(year), int(mon), int(day), int(hour))

def isMonday(db, b):
    dt = getdt(db, b)
    return dt.weekday() == 0 if dt is not None else False

def ndaysold(n, db, b):
    dt = getdt(db, b)
    if dt is not None and datetime.now() - dt > timedelta(days = n):
        return True
    else:
        return False

def doBackup(db, db_bkup_dir, timestamp):
    cmd         = "pg_dump -U dss %s > %s/%s.%s" % (db, db_bkup_dir, db, timestamp)
    print cmd
    os.system(cmd)

def rmBackups(db_bkup_dir, backups_to_remove):
    backups_to_remove.sort()
    for btr in backups_to_remove:
        cmd = "rm %s/%s" % (db_bkup_dir, btr)
        print "Removing:", cmd
        os.system(cmd)

if __name__ == "__main__":
    try:
        db, = sys.argv[1:]
    except ValueError:
        print "Please provide a database name."
        sys.exit()

    N = 2
    db_bkup_dir = "/home/dss/database_backups"
    timestamp   = datetime.now().strftime("%Y-%m-%d_%H:00:00")

    doBackup(db, db_bkup_dir, timestamp)

    if db == "dss":
        # DSS Backups
        rmBackups(db_bkup_dir, [b for b in os.listdir(db_bkup_dir) 
                       if db in b and ndaysold(N, db, b) and not isMonday(db, b)])
    elif db == "weather":
        # Weather Backups
        rmBackups(db_bkup_dir, [b for b in os.listdir(db_bkup_dir) if db in b and ndaysold(N, db, b)])
    else:
        print "No backup removal supported for %s."  % db
