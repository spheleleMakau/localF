from django import forms


class AddTrainingForm(forms.Form):
    training = forms.ChoiceField(choices=[
        ("course", "Group course - R500 non-refundable registration"),
        ("individual", "One-on-one training"),
    ])
    term = forms.ChoiceField(choices=[(str(n), f"Term {n}") for n in range(1, 5)])
    city = forms.ChoiceField(
        choices=[
            ("", "Select a city"),
            ("Durban", "Durban"),
            ("Johannesburg", "Johannesburg"),
            ("Cape Town", "Cape Town"),
            ("other", "Other city"),
        ],
        help_text="Group courses are available in Durban, Johannesburg and Cape Town. One-on-one is available in all cities.",
    )
    other_city = forms.CharField(
        label="Other city",
        max_length=120,
        required=False,
        help_text="If you selected Other city, enter your city for one-on-one training.",
    )
    hours = forms.IntegerField(min_value=1, max_value=10000, initial=1, required=False, help_text="For one-on-one training only (up to 10,000 hours per item).")

    def clean(self):
        data = super().clean()
        if data.get("training") == "individual" and data.get("hours") is None:
            self.add_error("hours", "Enter the number of hours for one-on-one training.")
        if data.get("city") == "other":
            if data.get("training") == "course":
                self.add_error("city", "Choose Durban, Johannesburg or Cape Town for the group course.")
            elif data.get("training") == "individual":
                if not data.get("other_city"):
                    self.add_error("other_city", "Enter your city for one-on-one training.")
                else:
                    data["city"] = data["other_city"]
        data.pop("other_city", None)
        if data.get("training") == "course":
            data["hours"] = 1
        return data


class AcademyOpportunityForm(forms.Form):
    city = forms.CharField(
        label="Your proposed city",
        max_length=120,
        help_text="Tell us where you would like to start your academy.",
    )
