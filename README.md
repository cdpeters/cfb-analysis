# **College Football Video Game Roster Analysis**

## **Overview of Project**
The following project analyzes three college football rosters from the dynasty
mode of a video game called EA Sports College Football 25 (CFB 25). The goal of
the project was to create a tool that would help make the recruiting portion of
the game easier by collecting data from different screens within the mode and
displaying it in a readily accessible and consistent format. The result of the
project is an app that allows a user to view a given roster, transform the
roster into alternate views, see visualizations related to roster construction,
and use pre-transformed views to assess possible players leaving and young
player quality.

### **Tools Used**
The project uses the `marimo` notebook framework for all of the analysis,
interactive UI elements, and for transformation of the notebook into a web app.
The `polars` library was used for loading the data and performing dataframe
transformations. `altair` was used for the visualizations. For the deployed app,
`httpx` is used to fetch the roster files from the repo, replacing the file
system read operations that are done when the notebook is run locally. The app
is deployed on GitHub Pages: [CFB 25 Roster Analysis
App](https://cdpeters.github.io/cfb-analysis/).

### **Roster Data**
The roster data is contained within three separate Excel files, one for each of
the three universities analyzed. Each sheet within the file contains the roster
for a given season (indicated by the sheet name). The Excel files are located in
the
[`data/datasets/`](https://github.com/cdpeters/cfb-analysis/tree/main/data/datasets)
folder of the repo.

### **Notebooks**
The `marimo` notebooks can be found in the `notebooks/` folder of the repo. The
primary analysis notebook that the web app is derived from and that contains all
of the analysis found in the app is
[roster_analysis.py](https://github.com/cdpeters/cfb-analysis/blob/main/notebooks/roster_analysis.py).
There is an additional analysis notebook
[roster_comparison.py](https://github.com/cdpeters/cfb-analysis/blob/main/notebooks/roster_comparison.py)
that aims to compare the three rosters of a given season directly but is
currently not yet finished. Lastly, the notebook
[players_leaving.py](https://github.com/cdpeters/cfb-analysis/blob/main/notebooks/players_leaving.py)
is for updating the roster files with a new sheet for the next season with the
seniors removed and the class standing for each player advanced by one year
(freshman to sophomore, sophomore to junior, etc.).

### **Additional Visualizations**
When the `roster_analysis.py` notebook is run locally, the visualizations that
get created for a specific university and season get saved in the
[`data/images/`](https://github.com/cdpeters/cfb-analysis/tree/main/data/images)
folder in the repo. There are also some images from the `roster_comparison.py`
notebook located in the same folder.

## **Analysis**


## **Future Plans**



<!-- <div align="center">
    <img src="assets/images/bike_sharing/ride_durations_by_all_users.svg"
         alt="Ride Durations by All Users" />
</div> -->
