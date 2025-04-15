package smartask.api.repositories;

import smartask.api.utils.CSVhandler;

import java.util.List;

public class FShandler {
    private final String path  = "../data/";
    private final String file1  = "Schedule.csv";
    private final String file2  = "Schedule2.csv";

    private final CSVhandler handler = new CSVhandler();

    public List<String[]> readex1(){
        return  handler.readCSV(path+file1);
    }
    public List<String[]> readex2(){
        return  handler.readCSV(path+file2);
    }

}
