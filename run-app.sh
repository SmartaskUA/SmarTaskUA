cd api
mvn install
cd ..
docker-compose down
docker-compose up --build
