# Change root password to 'vagrant'
echo "root:vagrant" | chpasswd

# Update package cache
apt-get update

# Install packages
apt-get install -y python-setuptools
apt-get install -y python-pip
apt-get install -y libpq-dev
apt-get install -y python-dev

pip install -r /rgserver/requirements.txt

apt-get install -y postgresql
apt-get install -y postgresql-client
apt-get install -y nginx
apt-get install -y dos2unix

cat /rgserver/vagrant/pg_hba.conf > /etc/postgresql/9.4/main/pg_hba.conf
/etc/init.d/postgresql restart
sudo -u postgres createuser --createdb robot
sudo -u postgres /usr/lib/postgresql/9.4/bin/createdb robot
sudo -u postgres /usr/lib/postgresql/9.4/bin/createdb robotgame
psql -U robot -h localhost < /rgserver/config/db_schema.sql

cp  /rgserver/vagrant/dbcon.py /rgserver/dbcon.py
cp /rgserver/vagrant/rgserver.conf /etc/nginx/sites-available/rgserver.conf
rm /etc/nginx/sites-enabled/default
ln -s /etc/nginx/sites-available/rgserver.conf /etc/nginx/sites-enabled/rgserver.conf

cp /rgserver/vagrant/rg /usr/bin/rg
dos2unix /usr/bin/rg
rg restart
