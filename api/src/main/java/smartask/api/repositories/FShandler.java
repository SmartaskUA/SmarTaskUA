package smartask.api.repositories;

import smartask.api.utils.CSVhandler;

import java.util.List;

public class FShandler {
    private final String path  = "../data/";
    private final String file  = "ex1.csv";

    private final CSVhandler handler = new CSVhandler();

    public List<String[]> readex1(){
        return  handler.readCSV(path+file);
    }

}
