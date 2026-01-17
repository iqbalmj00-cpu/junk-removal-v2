import { NextResponse } from 'next/server';

export async function POST() {
  return NextResponse.json({
    room_url: "https://jamalsjunk.daily.co/jamals-main",
  });
}
