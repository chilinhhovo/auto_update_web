# NYC Community board scrapper 
Live website: https://auto-update-web-1.onrender.com/ 

This repository contains auto-scrapper and dataframes for Community board (CB) minutes of Manhattan CB1,2 and 4, and Bronx CB1. 

## Why do we need this? 
Community boards in New York City are local government bodies that advise elected officials and government agencies on issues affecting their communities. Community boards are made up of 50 unsalaried members appointed by Borough Presidents. Members must reside, work, or have a specific interest in the community they represent. 

Each month, every community board in NYC gathers at their respective neighbourhood to discuss matters that are important to the commumity, from advising on land use and zoning, assessing community needs, addressing community concerns, handling complaints, planning local projects, processing applications, providing a public forum, etc. For this reason, community general board meeting minutes are very important to stay informed on the changes in your local area and for journalists who practice local journalism to pull information However, the community board meeting minutes are not centralised and soemtimes can be very difficult to find so I'm building a community board meeting minutes scrapper to have all minutes at one place. 

## About the data - Data files
Each community board has their one folder. In each folder, there is a folder for all the pdfs of the meeting minutes. 

Data files: 
>.csv - files that contain links to all pdfs from community boards
>-with-content.csv - files that contain links and content of the pdfs after parsing through pdfplumber
>.ipynb: jupyter notebooks for analysis

PDF folder: 
>[name]_PDFs - folders that contain PDF files of the meeting minutes 

App files: 
>app.py - Flask app that hosts all of the data
>requirements.txt- packages that have been used to develop this 

App folder: 
>static: contains geodata, font and logo files
>templates: contains all html files for display

Design folder: 
> Xd file.xd - Adobe XD file of website 1st design
> XD_screenshots - photos of website 1st design

Progress: 
>Data_diary.ipynb - thoughts and brief summary of the process, majority of the time, it was error message, fix, re-run, pray, and repeat 
 
