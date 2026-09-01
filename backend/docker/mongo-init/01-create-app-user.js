// Runs during the mongo image's own first-boot bootstrap, authenticated as
// MONGO_INITDB_ROOT_USERNAME/PASSWORD. Creates a second user scoped to
// readWrite+dbAdmin on the app's own database only -- the application itself
// never connects as root. mongosh exposes Node's process.env, so this can read
// the MONGO_APP_* variables docker-compose.yml passes to the container.
const dbName = process.env.MONGO_APP_DB;
const appUser = process.env.MONGO_APP_USER;
const appPassword = process.env.MONGO_APP_PASSWORD;

const appDb = db.getSiblingDB(dbName);

if (!appDb.getUser(appUser)) {
  appDb.createUser({
    user: appUser,
    pwd: appPassword,
    roles: [
      { role: "readWrite", db: dbName },
      { role: "dbAdmin", db: dbName },
    ],
  });
}
