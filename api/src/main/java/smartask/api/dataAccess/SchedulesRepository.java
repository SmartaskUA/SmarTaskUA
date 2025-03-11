package smartask.api.dataAccess;


import smartask.api.utils.CSVhandler;

import java.util.List;

// For now gonna use the only data we have access
public class SchedulesRepository
{
    private final String path  = "../data/";
    private final String file  = "ex1.csv";

    private final CSVhandler handler = new CSVhandler();

    public List<String[]> readex1(){
        return  handler.readCSV(path+file);
    }

}
