def build_resume_text(resume):

    data = resume["extracted_data"]
    print("collected data:")
    text = f"""
    Name: {data.get("name")}
    Job Title: {data.get("currentJobTitle")}
    Experience: {data.get("totalExperience")}
    Location: {data.get("city")}
    Skills: {", ".join(data.get("skills", []))}
    About: {data.get("aboutMe")}
    """

    for exp in data.get("experience", []):
        text += f"""
        Company: {exp.get("company")}
        Role: {exp.get("title")}
        Description: {exp.get("description")}
        """

    return text