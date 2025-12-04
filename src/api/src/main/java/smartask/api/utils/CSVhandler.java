package smartask.api.utils;

import com.opencsv.CSVReader;
import com.opencsv.bean.CsvToBean;
import com.opencsv.bean.CsvToBeanBuilder;
import org.springframework.stereotype.Service;

import java.io.FileReader;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class CSVhandler {

    // Method to read CSV and return list of string arrays
    public List<String[]> readCSV(String filePath) {
        List<String[]> data = new ArrayList<>();
        try (CSVReader reader = new CSVReader(new FileReader(filePath))) {
            data = reader.readAll();
        } catch (IOException e) {
            e.printStackTrace();
        }
        return data;
    }

    // Method to read CSV into a list of objects of a given class type
    public <T> List<T> readCSVToBean(String filePath, Class<T> clazz) {
        List<T> records = new ArrayList<>();
        try (FileReader fileReader = new FileReader(filePath)) {
            CsvToBean<T> csvToBean = new CsvToBeanBuilder<T>(fileReader)
                    .withType(clazz)
                    .withIgnoreLeadingWhiteSpace(true)
                    .build();
            records = csvToBean.parse();
        } catch (IOException e) {
            e.printStackTrace();
        }
        return records;
    }
}
