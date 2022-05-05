
# thesis-lienhop

Run 
```
pip install -r requirements.txt
```
to check for and install all required libraries.
</br>

This repository consists of several parts. The "Modules" folder contains several python modules. The "PythonAPP" folder contains jupyter notebooks, "main.ipynb" is the most important one. The "restServer" folder contains the fastAPI application, including the restful backend and the frontend.
</br>

To use the application and import the provided data, several steps are necessary. First, postgreSQL needs to be installed on the system (https://www.postgresql.org/download/) and some database and user credentials need to be available. Now, data can be imported to be made accessible. One viable dataset is included in the folder "data/speeches", consisting of XML files. Open the notebook "main.ipynb" and execute the first cell to import dependencies. In the next cell, change the credentials for the DBInterface to your postgreSQL standard settings. After connecting, execute the next cell to create a new database with the name "speeches". If the name of the database should be something different, you have to adjust the next cell to access the correct database. Execute the next cell to populate the newly created database. This might take a while...
</br>

Once the database is filled, you might have to change credentials for the database in "restServer/server.py". In a terminal, navigate to the "restServer" folder and execute the command 
```
uvicorn server:app --reload  
```
to start the server.