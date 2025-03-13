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
}
