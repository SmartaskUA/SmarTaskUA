package smartask.api.models.requests;


import lombok.*;

@AllArgsConstructor
@NoArgsConstructor
@Getter
@Setter
@ToString
public class RestrictionRequest {
    private String restrictionType;
    private String date;

    public String getRestrictionType(){return  this.restrictionType;}
    public String getDate(){return  this.date;}
}
