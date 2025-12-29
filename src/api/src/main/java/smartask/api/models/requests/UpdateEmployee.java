package smartask.api.models.requests;

import jakarta.validation.constraints.NotBlank;

public class UpdateEmployee {

    @NotBlank(message = "Name cannot be empty")
    private String name;

    public UpdateEmployee(String name) {
        this.name = name;
    }

    public UpdateEmployee() {
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }
}
