type DeliveryEmail = {
  to: string;
  subject: string;
  html: string;
};

export async function sendDeliveryEmail(email: DeliveryEmail) {
  const apiKey = process.env.RESEND_API_KEY;
  const from = process.env.EMAIL_FROM ?? "AI Digital Product Money Machine <noreply@example.com>";

  if (!apiKey || apiKey.includes("replace")) {
    console.log("Email delivery skipped. Configure RESEND_API_KEY to send:", {
      to: email.to,
      subject: email.subject
    });
    return { skipped: true };
  }

  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      from,
      to: email.to,
      subject: email.subject,
      html: email.html
    })
  });

  if (!response.ok) {
    throw new Error(`Resend failed with ${response.status}`);
  }

  return response.json();
}
