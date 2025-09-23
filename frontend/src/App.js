import React from "react";
import PaymentsTable from "./PaymentsTable";
import { Container, Typography } from "@mui/material";

function App() {
  return (
    <Container>
      <Typography variant="h4" align="center" sx={{ my: 4 }}>
        Payments Overview
      </Typography>
      <PaymentsTable />
    </Container>
  );
}

export default App;
